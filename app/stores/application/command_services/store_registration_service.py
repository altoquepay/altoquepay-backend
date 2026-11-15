from app.shared.domain.errors import BusinessError
from app.shared.infrastructure.unit_of_work import UnitOfWork
from app.stores.application.ports.store_administrators import StoreAdministrators
from app.stores.domain.model.aggregates.store import Store
from app.stores.domain.model.commands.register_store_command import RegisterStoreCommand
from app.stores.domain.repositories.store_repository import StoreRepository


class StoreRegistrationService:
    def __init__(
        self,
        stores: StoreRepository,
        administrators: StoreAdministrators,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._stores = stores
        self._administrators = administrators
        self._unit_of_work = unit_of_work

    async def register(self, command: RegisterStoreCommand) -> Store:
        """Save the store and its administrator together, or neither if one is not valid."""
        # shortcut: two simultaneous registrations can both pass this check, and the unique
        # constraint then rejects one with a 500; map IntegrityError to 409 if that ever happens.
        if await self._stores.exists_by_ruc(command.ruc):
            raise BusinessError(
                "RUC_TAKEN", "A store with this RUC is already registered.", field="ruc", status=409
            )
        store = Store.register(command.business_name, command.ruc)
        await self._stores.add(store)
        if store.id is None:
            raise ValueError("The store was not stored.")
        await self._administrators.create(
            command.admin_email, command.admin_full_name, command.admin_password, store.id
        )
        await self._unit_of_work.commit()
        return store

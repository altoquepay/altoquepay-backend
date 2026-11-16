from app.regulation.domain.model.aggregates.bcrp_cap import BcrpCap
from app.regulation.infrastructure.persistence.models import BcrpCapModel
from app.shared.domain.value_objects import Rate


def to_domain(model: BcrpCapModel) -> BcrpCap:
    return BcrpCap(
        max_tea=Rate.from_percent(model.max_tea),
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        created_by=model.created_by,
        id=model.id,
    )


def to_model(cap: BcrpCap) -> BcrpCapModel:
    return BcrpCapModel(
        max_tea=cap.max_tea.percent,
        valid_from=cap.valid_from,
        valid_to=cap.valid_to,
        created_by=cap.created_by,
    )

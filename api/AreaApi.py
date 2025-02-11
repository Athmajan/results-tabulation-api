from util import RequestBody, get_area_type

from schemas import AreaSchema as Schema
from orm.entities import Area
import connexion


def get_all(electionId=None, areaName=None, associatedAreaId=None, areaType=None):
    result = Area.get_all(
        election_id=electionId,
        area_name=areaName,
        associated_area_id=associatedAreaId,
        area_type=get_area_type(area_type=areaType)
    )

    return Schema(many=True).dump(result).data

from app import db
from orm.entities import Office
from orm.enums import OfficeTypeEnum, AreaTypeEnum
from sqlalchemy.orm import relationship, synonym


class CountingCentreModel(Office.Model):
    __mapper_args__ = {
        'polymorphic_identity': AreaTypeEnum.CountingCentre
    }


Model = CountingCentreModel


def create(officeName, electionId):
    result = Model(
        officeName=officeName,
        electionId=electionId
    )

    return result

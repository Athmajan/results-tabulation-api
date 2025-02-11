from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property

from app import db
from sqlalchemy.orm import relationship
from sqlalchemy import func

from util import get_paginated_query

from orm.entities import Election, Office, Proof, History, SubmissionVersion, Area

from orm.enums import SubmissionTypeEnum, ProofTypeEnum


class SubmissionModel(db.Model):
    __tablename__ = 'submission'
    submissionId = db.Column(db.Integer, db.ForeignKey(History.Model.__table__.c.historyId), primary_key=True)
    submissionType = db.Column(db.Enum(SubmissionTypeEnum), nullable=False)
    electionId = db.Column(db.Integer, db.ForeignKey(Election.Model.__table__.c.electionId), nullable=False)
    areaId = db.Column(db.Integer, db.ForeignKey(Office.Model.__table__.c.areaId), nullable=False)
    submissionProofId = db.Column(db.Integer, db.ForeignKey(Proof.Model.__table__.c.proofId), nullable=False)
    latestVersionId = db.Column(db.Integer, db.ForeignKey("submissionVersion.submissionVersionId"), nullable=True)

    election = relationship(Election.Model, foreign_keys=[electionId])
    area = relationship(Area.Model, foreign_keys=[areaId])
    submissionProof = relationship(Proof.Model, foreign_keys=[submissionProofId])
    submissionHistory = relationship(History.Model, foreign_keys=[submissionId])
    latestVersion = relationship("SubmissionVersionModel", foreign_keys=[latestVersionId])
    versions = relationship("SubmissionVersionModel", order_by="desc(SubmissionVersionModel.submissionVersionId)",
                            primaryjoin="SubmissionModel.submissionId==SubmissionVersionModel.submissionId")

    def set_latest_version(self, submissionVersionId):
        self.latestVersionId = submissionVersionId

        db.session.add(self)
        db.session.flush()

    def __init__(self, submissionType, electionId, areaId):
        submissionProof = Proof.create(proofType=get_submission_proof_type(submissionType=submissionType))
        submissionHistory = History.create()

        super(SubmissionModel, self).__init__(
            submissionId=submissionHistory.historyId,
            electionId=electionId,
            submissionType=submissionType,
            areaId=areaId,
            submissionProofId=submissionProof.proofId
        )

        db.session.add(self)
        db.session.flush()


Model = SubmissionModel


def get_by_id(submissionId):
    result = Model.query.filter(
        Model.submissionId == submissionId
    ).one_or_none()

    return result


def get_all(electionId=None, officeId=None):
    query = Model.query

    if electionId is not None:
        query = query.filter(Model.electionId == electionId)

    if officeId is not None:
        query = query.filter(Model.areaId == officeId)

    result = get_paginated_query(query).all()

    return result


def get_submission_proof_type(submissionType):
    if submissionType is SubmissionTypeEnum.TallySheet:
        return ProofTypeEnum.ManuallyFilledTallySheets
    elif submissionType is SubmissionTypeEnum.Report:
        return ProofTypeEnum.ManuallyFilledReports

    return None


def create(submissionType, electionId, areaId):
    result = Model(
        electionId=electionId,
        submissionType=submissionType,
        areaId=areaId
    )

    return result

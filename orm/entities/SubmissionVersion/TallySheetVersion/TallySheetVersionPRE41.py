from flask import render_template
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy import func

from app import db
from exception import NotFoundException, ForbiddenException
from orm.entities import Candidate, Party, Area
from orm.entities.Election import ElectionCandidate
from orm.entities.SubmissionVersion import TallySheetVersion
from orm.entities.TallySheetVersionRow import TallySheetVersionRow_PRE_41, TallySheetVersionRow_RejectedVoteCount
from util import get_paginated_query

from orm.entities.Submission import TallySheet
from orm.enums import TallySheetCodeEnum, AreaTypeEnum
from sqlalchemy import and_


class TallySheetVersionPRE41Model(TallySheetVersion.Model):

    def __init__(self, tallySheetId):
        super(TallySheetVersionPRE41Model, self).__init__(
            tallySheetId=tallySheetId
        )

    def html(self):

        tallySheetContent = self.content
        summary = self.summary

        print("############# heyyyyy")

        content = {
            "title": "PRESIDENTIAL ELECTION ACT NO. 15 OF 1981",
            "electoralDistrict": Area.get_associated_areas(
                self.submission.area, AreaTypeEnum.ElectoralDistrict)[0].areaName,
            "pollingDivision": Area.get_associated_areas(
                self.submission.area, AreaTypeEnum.PollingDivision)[0].areaName,
            "countingCentre": self.submission.area.areaName,
            "pollingDistrictNos": ", ".join([
                pollingDistrict.areaName for pollingDistrict in
                Area.get_associated_areas(self.submission.area, AreaTypeEnum.PollingDistrict)
            ]),
            "data": [
            ],
            "total": summary.validVoteCount,
            "rejectedVotes": summary.rejectedVoteCount,
            "grandTotal": summary.totalVoteCount
        }

        for row_index in range(len(tallySheetContent)):
            row = tallySheetContent[row_index]
            if row.count is not None:
                content["data"].append([
                    row_index + 1,
                    row.candidateName,
                    row.partySymbol,
                    row.countInWords,
                    row.count,
                    ""
                ])
            else:
                content["data"].append([
                    row_index + 1,
                    row.candidateName,
                    row.partySymbol,
                    "",
                    "",
                    ""
                ])

        html = render_template(
            'PRE-41.html',
            content=content
        )

        return html

    __mapper_args__ = {
        'polymorphic_identity': TallySheetCodeEnum.PRE_41
    }

    def add_row(self, candidateId, count, countInWords=None):
        from orm.entities.TallySheetVersionRow import TallySheetVersionRow_PRE_41

        TallySheetVersionRow_PRE_41.create(
            tallySheetVersionId=self.tallySheetVersionId,
            candidateId=candidateId,
            count=count,
            countInWords=countInWords
        )

    def add_invalid_vote_count(self, electionId, rejectedVoteCount):
        TallySheetVersionRow_RejectedVoteCount.create(
            electionId=electionId,
            tallySheetVersionId=self.tallySheetVersionId,
            rejectedVoteCount=rejectedVoteCount
        )

    @hybrid_property
    def content(self):

        return db.session.query(
            ElectionCandidate.Model.candidateId,
            Candidate.Model.candidateName,
            Party.Model.partySymbol,
            TallySheetVersionRow_PRE_41.Model.count,
            TallySheetVersionRow_PRE_41.Model.countInWords
        ).join(
            TallySheetVersionRow_PRE_41.Model,
            and_(
                TallySheetVersionRow_PRE_41.Model.candidateId == ElectionCandidate.Model.candidateId,
                TallySheetVersionRow_PRE_41.Model.tallySheetVersionId == self.tallySheetVersionId,
            ),
            isouter=True
        ).join(
            Candidate.Model,
            Candidate.Model.candidateId == ElectionCandidate.Model.candidateId,
            isouter=True
        ).join(
            Party.Model,
            Party.Model.partyId == ElectionCandidate.Model.partyId,
            isouter=True
        ).filter(
            ElectionCandidate.Model.electionId.in_(self.submission.election.mappedElectionIds)
        ).all()

    def area_wise_valid_vote_count(self):
        return db.session.query(
            TallySheetVersionRow_PRE_41.Model.tallySheetVersionId,
            func.sum(TallySheetVersionRow_PRE_41.Model.count).label("validVoteCount")
        ).filter(
            TallySheetVersionRow_PRE_41.Model.tallySheetVersionId == self.tallySheetVersionId
        )

    def area_wise_rejected_vote_count(self):
        return db.session.query(
            TallySheetVersionRow_RejectedVoteCount.Model.tallySheetVersionId,
            func.sum(TallySheetVersionRow_RejectedVoteCount.Model.rejectedVoteCount).label("rejectedVoteCount"),
        ).filter(
            TallySheetVersionRow_RejectedVoteCount.Model.tallySheetVersionId == self.tallySheetVersionId,
            TallySheetVersionRow_RejectedVoteCount.Model.candidateId == None
        )

    @hybrid_property
    def summary(self):
        area_wise_valid_vote_count_subquery = self.area_wise_valid_vote_count().subquery()
        area_wise_rejected_vote_count_subquery = self.area_wise_rejected_vote_count().subquery()

        return db.session.query(
            func.count(TallySheetVersion.Model.tallySheetVersionId).label("areaCount"),
            func.sum(area_wise_valid_vote_count_subquery.c.validVoteCount).label("validVoteCount"),
            func.sum(area_wise_rejected_vote_count_subquery.c.rejectedVoteCount).label("rejectedVoteCount"),
            func.sum(
                area_wise_valid_vote_count_subquery.c.validVoteCount +
                area_wise_rejected_vote_count_subquery.c.rejectedVoteCount
            ).label("totalVoteCount")
        ).join(
            area_wise_valid_vote_count_subquery,
            area_wise_valid_vote_count_subquery.c.tallySheetVersionId == TallySheetVersion.Model.tallySheetVersionId,
            isouter=True
        ).join(
            area_wise_rejected_vote_count_subquery,
            area_wise_rejected_vote_count_subquery.c.tallySheetVersionId == TallySheetVersion.Model.tallySheetVersionId,
            isouter=True
        ).filter(
            TallySheetVersion.Model.tallySheetVersionId == self.tallySheetVersionId
        ).one_or_none()


Model = TallySheetVersionPRE41Model


def get_all(tallySheetId):
    query = Model.query.filter(Model.tallySheetId == tallySheetId)

    result = get_paginated_query(query).all()

    return result


def get_by_id(tallySheetId, tallySheetVersionId):
    tallySheet = TallySheet.get_by_id(tallySheetId=tallySheetId)
    if tallySheet is None:
        raise NotFoundException("Tally sheet not found. (tallySheetId=%d)" % tallySheetId)
    elif tallySheet.tallySheetCode is not TallySheetCodeEnum.PRE_41:
        raise NotFoundException("Requested version not found. (tallySheetId=%d)" % tallySheetId)

    result = Model.query.filter(
        Model.tallySheetVersionId == tallySheetVersionId
    ).one_or_none()

    return result


def create(tallySheetId):
    result = Model(tallySheetId=tallySheetId)

    return result

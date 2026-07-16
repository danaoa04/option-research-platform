from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.data.provider_api import ProviderApiService
from backend.data.provider_cli import main
from backend.data.provider_operations import ProviderOperationsService
from backend.database.models.base import Base
from backend.database.provider_operations import ProviderOperationsRepository


def test_cli_and_api_are_deterministic_redacted_and_fail_nonzero(capsys):
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["data"]["data"] == ["cboe", "databento", "orats", "polygon"]
    assert main(["job-status", "--id", "missing"]) == 2
    assert "error" in capsys.readouterr().err
    api = ProviderApiService()
    assert api.capabilities("polygon").data["option_quotes"] is False
    assert "<script>" not in api.export_html("<script>", {"api_key": "secret"})


def test_durable_artifacts_are_immutable_and_queryable():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = ProviderOperationsRepository(session)
        repository.create_job("job-1", "orats", "a" * 64, {})
        repository.append_event("job-1", "completed")
        artifact = repository.persist_artifact(
            "cert-1",
            "orats",
            "certification",
            {"quality": 1.0},
            "b" * 64,
            job_id="job-1",
        )
        session.commit()
        assert repository.events("job-1")[0].status == "completed"
        assert repository.artifacts("certification")[0].artifact_id == artifact.artifact_id
        try:
            repository.persist_artifact(
                "cert-1", "orats", "certification", {}, "c" * 64, job_id="job-1"
            )
        except ValueError as exc:
            assert "Immutable" in str(exc)
        else:
            raise AssertionError("changed artifact was accepted")


def test_cancel_resume_history_is_exposed():
    operations = ProviderOperationsService()
    job = operations.create_job("cboe", {"dataset": "fixture"})
    service = ProviderApiService(operations)
    service.cancel(job.job_id)
    service.resume(job.job_id)
    assert [event[0].value for event in service.events(job.job_id).data] == [
        "cancelled",
        "planned",
    ]

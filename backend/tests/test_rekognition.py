"""Tests for Amazon Rekognition client parsing and provider resolution."""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.main import resolve_provider
from app.vision.mock import MockVisionClient
from app.vision.rekognition import AwsRekognitionClient


def test_parse_labels_maps_instances_to_detections():
    labels = [
        {
            "Name": "Car",
            "Confidence": 98.5,
            "Instances": [
                {
                    "Confidence": 97.0,
                    "BoundingBox": {"Left": 0.1, "Top": 0.2, "Width": 0.3, "Height": 0.4},
                }
            ],
        },
        {
            "Name": "Outdoor",
            "Confidence": 90.0,
            "Instances": [],  # scene label — skip
        },
    ]
    dets = AwsRekognitionClient._parse_labels(labels)
    assert len(dets) == 1
    assert dets[0].label == "car"
    assert dets[0].confidence == 0.97
    assert dets[0].x == 0.1
    assert dets[0].y == 0.2
    assert dets[0].w == 0.3
    assert dets[0].h == 0.4


@pytest.mark.asyncio
async def test_detect_objects_calls_rekognition():
    fake_response = {
        "Labels": [
            {
                "Name": "Person",
                "Confidence": 88.0,
                "Instances": [
                    {
                        "Confidence": 88.0,
                        "BoundingBox": {"Left": 0.0, "Top": 0.0, "Width": 0.5, "Height": 0.5},
                    }
                ],
            }
        ]
    }
    with patch("app.vision.rekognition.boto3.client") as mock_boto:
        client = MagicMock()
        client.detect_labels.return_value = fake_response
        mock_boto.return_value = client
        vision = AwsRekognitionClient(region="us-east-1", min_gap_seconds=0)
        dets = await vision.detect_objects(b"fake-jpeg")
        assert len(dets) == 1
        assert dets[0].label == "person"
        client.detect_labels.assert_called_once()


def test_resolve_provider_rekognition_without_creds_falls_back(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    settings = Settings(
        vision_provider="rekognition",
        aws_access_key_id="",
        aws_secret_access_key="",
    )
    name, client = resolve_provider(settings)
    assert name == "mock"
    assert isinstance(client, MockVisionClient)


def test_resolve_provider_auto_picks_rekognition(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    settings = Settings(
        vision_provider="auto",
        azure_vision_key="",
        aws_access_key_id="AKIATEST",
        aws_secret_access_key="secret",
        aws_region="us-west-2",
    )
    with patch("app.main.AwsRekognitionClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        name, _ = resolve_provider(settings)
        assert name == "rekognition"
        mock_cls.assert_called_once()

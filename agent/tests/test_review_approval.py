"""Regression coverage for failed sends in the approval endpoint."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from car_agent.api.routes import reviews
from car_agent.clients.email import EmailResult


class ReviewApprovalTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.row = SimpleNamespace(
            status="pending",
            kind="negotiation_stage_email",
            customer=SimpleNamespace(email="customer@example.com"),
            payload={
                "email": {"to": "dealer@example.com", "subject": "Availability"},
                "graph": {"thread_id": "neg-1"},
            },
        )

        async def finalize(**kwargs):
            self.row.status = kwargs["status"]
            return self.row

        self.enterContext(patch.dict("os.environ", {"REVIEW_API_TOKEN": "test-token"}))
        self.enterContext(patch.object(reviews, "get_checkpoint", AsyncMock(return_value=self.row)))
        self.send = self.enterContext(patch.object(reviews, "send_email", AsyncMock()))
        self.finalize = self.enterContext(
            patch.object(reviews, "finalize_checkpoint", AsyncMock(side_effect=finalize))
        )
        self.resume = self.enterContext(
            patch.object(reviews, "_resume_graph", AsyncMock(return_value=True))
        )
        app = FastAPI()
        app.include_router(reviews.router)
        self.client = await self.enterAsyncContext(AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Review-Token": "test-token"},
        ))

    async def test_failed_send_stays_pending_and_can_be_approved_again(self):
        self.send.side_effect = [
            EmailResult(success=False, message_id=None, dry_run=False, error="Send rejected"),
            EmailResult(success=True, message_id="sent-1", dry_run=False),
        ]

        failed = await self.client.post("/api/reviews/checkpoint-1/approve")

        self.assertEqual(failed.status_code, 502)
        self.assertIn("Send rejected", failed.json()["detail"])
        self.assertEqual(self.row.status, "pending")
        self.finalize.assert_not_awaited()
        self.resume.assert_not_awaited()

        retried = await self.client.post("/api/reviews/checkpoint-1/approve")

        self.assertEqual(retried.status_code, 200)
        self.assertTrue(retried.json()["success"])
        self.assertEqual(self.row.status, "approved")
        self.assertEqual(self.send.await_count, 2)
        self.finalize.assert_awaited_once()
        self.resume.assert_awaited_once_with(
            thread_id="neg-1",
            payload={"approved": True, "message_id": "sent-1"},
            expect_waiting_for="dealer_reply",
        )

    async def test_dry_run_still_advances(self):
        self.send.return_value = EmailResult(
            success=True, message_id="dry-run", dry_run=True
        )

        response = await self.client.post("/api/reviews/checkpoint-1/approve")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["send_result"]["dry_run"])
        self.assertEqual(self.row.status, "approved")
        self.resume.assert_awaited_once()

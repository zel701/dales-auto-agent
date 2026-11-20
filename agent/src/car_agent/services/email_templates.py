"""Branded HTML email templates."""

from __future__ import annotations

from datetime import date


def build_otp_email(code: str) -> dict[str, str]:
    """Render the login one-time-code email."""
    body_content = f"""<p style="margin: 0 0 16px; font-family: 'Lato', Arial, sans-serif; font-size: 15px; color: #4a4a4a; line-height: 1.6;">
  Use this code to sign in. It expires in 10 minutes.
</p>
<div style="text-align: center; margin: 24px 0;">
  <div style="display: inline-block; background-color: #f7f7f7; border-radius: 8px; padding: 18px 32px; font-family: 'Courier New', monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #161616;">
    {code}
  </div>
</div>
<p style="margin: 24px 0 0; font-family: 'Lato', Arial, sans-serif; font-size: 13px; color: #999; line-height: 1.5;">
  If you didn't request this, you can ignore this email.
</p>"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f7f7f7; font-family: 'Lato', Arial, sans-serif; color: #4a4a4a;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f7f7f7; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <tr>
            <td style="background-color: #ff0083; padding: 32px 40px; text-align: center;">
              <h1 style="margin: 0; color: #ffffff; font-family: 'Merriweather', Georgia, serif; font-size: 24px; font-weight: 700;">
                Your sign-in code
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px;">
              {body_content}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return {
        "subject": f"Your sign-in code: {code}",
        "html_body": body_content,
        "full_html": full_html,
    }

_PAYMENT_LABELS = {"finance": "Finance", "cash": "Cash"}
_DELIVERY_LABELS = {"pickup": "Pick up myself", "ship": "Ship to my home"}


def wrap_analysis_email(
    body_content: str,
    car_info: dict[str, str],
    results_url: str,
) -> str:
    """Wrap LLM-generated content in the branded email shell."""
    make = car_info["make"]
    model = car_info["model"]
    trim = "/".join(car_info.get("trims") or [])

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f7f7f7; font-family: 'Lato', Arial, sans-serif; color: #4a4a4a;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f7f7f7; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <tr>
            <td style="background-color: #ff0083; padding: 32px 40px; text-align: center;">
              <h1 style="margin: 0; color: #ffffff; font-family: 'Merriweather', Georgia, serif; font-size: 24px; font-weight: 700;">
                Your {make} {model} {trim} Analysis
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px;">
              {body_content}
              <div style="text-align: center; margin: 36px 0 12px;">
                <a href="{results_url}" style="display: inline-block; background-color: #ff0083; color: #ffffff; font-family: 'Lato', Arial, sans-serif; font-size: 16px; font-weight: 700; text-decoration: none; padding: 16px 40px; border-radius: 8px;">
                  Let Us Negotiate For You
                </a>
                <p style="margin: 12px 0 0; font-size: 13px; color: #999;">
                  View all {make} {model} listings and pick the ones you want us to negotiate.
                </p>
              </div>
              <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0 24px;">
              <p style="margin: 0; font-size: 12px; color: #b0b0b0; text-align: center;">
                You received this email because you requested a car analysis.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def wrap_order_confirmation_email(body_content: str, car_info: dict[str, str]) -> str:
    """Branded shell for order-confirmation emails (no CTA)."""
    make = car_info.get("make", "")
    model = car_info.get("model", "")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f7f7f7; font-family: 'Lato', Arial, sans-serif; color: #4a4a4a;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f7f7f7; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
          <tr>
            <td style="background-color: #ff0083; padding: 32px 40px; text-align: center;">
              <h1 style="margin: 0; color: #ffffff; font-family: 'Merriweather', Georgia, serif; font-size: 24px; font-weight: 700;">
                Order Received — {make} {model}
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px;">
              {body_content}
              <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0 24px;">
              <p style="margin: 0; font-size: 12px; color: #b0b0b0; text-align: center;">
                You received this email because you submitted a negotiation request.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_order_confirmation_email(
    car_info: dict[str, str],
    selected_count: int,
    need_by_date: date,
    payment_method: str,
    delivery_method: str,
) -> dict[str, str]:
    """Render the short order-confirmation email (subject + bodies)."""
    make = car_info.get("make", "")
    model = car_info.get("model", "")
    payment_label = _PAYMENT_LABELS.get(payment_method, payment_method)
    delivery_label = _DELIVERY_LABELS.get(delivery_method, delivery_method)
    formatted_date = f"{need_by_date.strftime('%B')} {need_by_date.day}, {need_by_date.year}"
    plural = "s" if selected_count != 1 else ""

    body_content = f"""<p style="margin: 0 0 16px; font-family: 'Lato', Arial, sans-serif; font-size: 15px; color: #4a4a4a; line-height: 1.6;">
  Thanks for trusting us with your {make} {model}. We've received your request and our team is on it.
</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f7f7f7; border-radius: 8px; padding: 16px; margin: 0 0 20px;">
  <tr><td style="padding: 4px 0; font-size: 14px; color: #777;">Listings to negotiate</td><td align="right" style="padding: 4px 0; font-size: 14px; color: #161616; font-weight: 600;">{selected_count} listing{plural}</td></tr>
  <tr><td style="padding: 4px 0; font-size: 14px; color: #777;">Need by</td><td align="right" style="padding: 4px 0; font-size: 14px; color: #161616; font-weight: 600;">{formatted_date}</td></tr>
  <tr><td style="padding: 4px 0; font-size: 14px; color: #777;">Payment</td><td align="right" style="padding: 4px 0; font-size: 14px; color: #161616; font-weight: 600;">{payment_label}</td></tr>
  <tr><td style="padding: 4px 0; font-size: 14px; color: #777;">Delivery</td><td align="right" style="padding: 4px 0; font-size: 14px; color: #161616; font-weight: 600;">{delivery_label}</td></tr>
</table>
<p style="margin: 0; font-family: 'Lato', Arial, sans-serif; font-size: 15px; color: #4a4a4a; line-height: 1.6;">
  We'll reach out within 1–2 business days with next steps.
</p>"""

    full_html = wrap_order_confirmation_email(body_content, car_info)
    return {
        "subject": f"We received your {make} {model} request",
        "html_body": body_content,
        "full_html": full_html,
    }

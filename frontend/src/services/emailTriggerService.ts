import { EmailTriggerRule, EmailTier, PassengerEmailPayload } from "../lib/email-types";

const TRIGGER_RULES: EmailTriggerRule[] = [
  {
    minRiskThreshold: 0,
    maxRiskThreshold: 50,
    tier: "Optimal",
    action: "Silent monitoring / No email",
    subject: "Flight Update: Optimal Condition",
    requiresRebooking: false,
  },
  {
    minRiskThreshold: 50,
    maxRiskThreshold: 70,
    tier: "Monitoring",
    action: "Monitoring Advisory (Buffer check)",
    subject: "Flight Advisory: Connection Buffer Check",
    requiresRebooking: false,
  },
  {
    minRiskThreshold: 70,
    maxRiskThreshold: 85,
    tier: "Warning",
    action: "Delay Warning + Alternative Flights",
    subject: "Travel Alert: Delay Risk Detected | Action Recommended",
    requiresRebooking: true,
  },
  {
    minRiskThreshold: 85,
    maxRiskThreshold: 100,
    tier: "Critical",
    action: "Critical Alert + Recommended Rebooking",
    subject: "CRITICAL: Major Delay Risk | Immediate Action Required",
    requiresRebooking: true,
  },
];

export function evaluateEmailTriggerRule(riskScore: number): EmailTriggerRule {
  const rule = TRIGGER_RULES.find(
    (r) => riskScore >= r.minRiskThreshold && riskScore <= r.maxRiskThreshold
  );
  return rule ?? TRIGGER_RULES[3]; // Default to Critical if out of bounds (shouldn't happen)
}

// A heuristic to convert delay minutes into a risk score (0-100)
export function calculateRiskScore(delayMin: number): number {
  if (delayMin <= 15) return 20;
  if (delayMin <= 30) return 45;
  if (delayMin <= 60) return 65;
  if (delayMin <= 90) return 80;
  return 95;
}

export function generateRecoveryEmailHtml(payload: Omit<PassengerEmailPayload, "bodyHtml">): string {
  const {
    passengerName,
    flightNo,
    origin,
    destination,
    scheduledDep,
    delayMin,
    reason,
    rebookingLinks,
    pnr
  } = payload;

  return `
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: 'Inter', -apple-system, sans-serif; background-color: #ffffff; margin: 0; padding: 20px; color: #18181b; line-height: 1.6; }
  .container { max-width: 600px; margin: 0 auto; }
  .highlight-blue { color: #2563eb; font-weight: 600; }
  .highlight-red { color: #dc2626; font-weight: 600; }
  .strong-text { font-weight: 700; color: #000000; }
  .options-box { background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 20px; margin: 24px 0; }
  .options-title { color: #0369a1; font-weight: 600; margin-top: 0; margin-bottom: 12px; }
  ul { margin: 0; padding-left: 20px; color: #334155; }
  li { margin-bottom: 8px; }
  a { color: #2563eb; text-decoration: underline; font-weight: 500; }
  .footer { margin-top: 32px; color: #334155; }
</style>
</head>
<body>
  <div class="container">
    <p class="strong-text" style="font-size: 16px;">Dear ${passengerName},</p>
    
    <p>We regret to inform you that your upcoming flight <span class="highlight-blue">${flightNo}</span> from <span class="strong-text">${origin}</span> to <span class="strong-text">${destination}</span> scheduled for departure at ${scheduledDep} has been delayed by approximately <span class="highlight-red">${delayMin} minutes</span> due to ${reason}.</p>
    
    ${payload.isActionable ? `
    <div class="options-box">
      <div class="options-title">Your Automated Recovery Options & Voucher:</div>
      <ul>
        <li>Complimentary $45 Executive Airport Lounge & Refreshment Voucher (Code: <span class="strong-text">FLITZ-VOUCHER-${pnr}</span>)</li>
        <li>Instant 1-Click Alternate Flight Rebooking Portal with guaranteed seat protection</li>
        <li>Free Priority Baggage Transfer across all partner airlines</li>
      </ul>
    </div>
    
    <p>You can view live route updates and select your preferred alternate flight at: <a href="${rebookingLinks.directUrl}">${rebookingLinks.directUrl}</a></p>
    ` : `
    <p>We are actively monitoring your flight and will provide further updates as they become available. At this time, no action is required.</p>
    `}
    
    <div class="footer">
      Sincerely,<br/>
      <span class="strong-text">Flitzzz Operations Center</span>
    </div>
  </div>
</body>
</html>
  `;
}

export function buildEmailPayload(
  passengerName: string,
  passengerEmail: string,
  pnr: string,
  seat: string,
  flightClass: string,
  flightId: string,
  flightNo: string,
  origin: string,
  destination: string,
  scheduledDep: string,
  delayMin: number,
  reason: string
): PassengerEmailPayload {
  
  const riskScore = calculateRiskScore(delayMin);
  const rule = evaluateEmailTriggerRule(riskScore);

  const directUrl = `https://flightwise-ai.com/rebook?pnr=${pnr}&flight=${flightId}`;

  const partialPayload: Omit<PassengerEmailPayload, "bodyHtml"> = {
    passengerName,
    passengerEmail,
    pnr,
    seat,
    flightClass,
    flightId,
    flightNo,
    origin,
    destination,
    scheduledDep,
    delayMin,
    reason,
    tier: rule.tier,
    subject: rule.subject,
    isActionable: rule.requiresRebooking,
    rebookingLinks: {
      directUrl,
    },
  };

  const bodyHtml = generateRecoveryEmailHtml(partialPayload);

  return {
    ...partialPayload,
    bodyHtml,
  };
}

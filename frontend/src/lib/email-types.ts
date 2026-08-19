export type EmailTier = "Optimal" | "Monitoring" | "Warning" | "Critical";

export interface EmailTriggerRule {
  minRiskThreshold: number;
  maxRiskThreshold: number;
  tier: EmailTier;
  action: string;
  subject: string;
  requiresRebooking: boolean;
}

export interface PassengerEmailPayload {
  passengerName: string;
  passengerEmail: string;
  pnr: string;
  seat: string;
  flightClass: string;
  flightId: string;
  flightNo: string;
  origin: string;
  destination: string;
  scheduledDep: string;
  delayMin: number;
  reason: string;
  tier: EmailTier;
  subject: string;
  bodyHtml: string;
  isActionable: boolean;
  rebookingLinks: {
    directUrl: string;
  };
}

export interface EmailDispatchLog {
  id: string;
  passenger: string;
  flight: string;
  timestamp: string;
  tier: EmailTier;
  status: "Sent" | "Failed";
}

export interface DemoTeammate {
  name: string;
  email: string;
  seat: string;
  class: string;
}

export const TEAMMATE_PRESETS: DemoTeammate[] = [
  { name: "Sri Poojaka", email: "sripoojaka11@gmail.com", seat: "04A", class: "Business Class" },
  { name: "Hema Krishna", email: "hemakrishna742006@gmail.com", seat: "12C", class: "Premium Economy" },
  { name: "Sai Sudhan", email: "saisudhanchinnaiyah@gmail.com", seat: "18D", class: "Economy" },
  { name: "Sakthi Lakshman", email: "sakthilakshman521@gmail.com", seat: "01A", class: "First Class" },
  { name: "Sheeba Salaman", email: "sheebasalaman@gmail.com", seat: "22F", class: "Economy" },
  { name: "Rithik Kumar", email: "rithikvkumar1475@gmail.com", seat: "07B", class: "Business Class" }
];

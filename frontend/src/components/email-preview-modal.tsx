import React, { useState } from "react";
import { PassengerEmailPayload } from "../lib/email-types";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Mail, Copy, Check, ExternalLink } from "lucide-react";
import { toast } from "sonner";

interface EmailPreviewModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  payload: PassengerEmailPayload | null;
}

export function EmailPreviewModal({ isOpen, onOpenChange, payload }: EmailPreviewModalProps) {
  const [copied, setCopied] = useState(false);

  if (!payload) return null;

  const handleCopyHtml = async () => {
    try {
      await navigator.clipboard.writeText(payload.bodyHtml);
      setCopied(true);
      toast.success("HTML Copied to Clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy HTML");
    }
  };

  const handleOpenMailClient = () => {
    let plainTextBody = `Dear ${payload.passengerName},\n\nWe regret to inform you that your upcoming flight ${payload.flightNo} from ${payload.origin} to ${payload.destination} scheduled for departure at ${payload.scheduledDep} has been delayed by approximately ${payload.delayMin} minutes due to ${payload.reason}.\n\n`;
    
    if (payload.isActionable) {
      plainTextBody += `Your Automated Recovery Options & Voucher:\n- Complimentary $45 Executive Airport Lounge & Refreshment Voucher (Code: FLITZ-VOUCHER-${payload.pnr})\n- Instant 1-Click Alternate Flight Rebooking Portal with guaranteed seat protection\n- Free Priority Baggage Transfer across all partner airlines\n\nYou can view live route updates and select your preferred alternate flight at: ${payload.rebookingLinks.directUrl}\n\n`;
    } else {
      plainTextBody += `We are actively monitoring your flight and will provide further updates as they become available. At this time, no action is required.\n\n`;
    }
    
    plainTextBody += `Sincerely,\nFlitzzz Operations Center`;

    const mailtoUrl = `mailto:${payload.passengerEmail}?subject=${encodeURIComponent(payload.subject)}&body=${encodeURIComponent(plainTextBody)}`;
    window.location.href = mailtoUrl;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col p-0 overflow-hidden bg-zinc-950 border-zinc-800 text-zinc-100">
        <DialogHeader className="p-6 border-b border-zinc-800/60 bg-zinc-900/50">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2 text-xl">
                <Mail className="h-5 w-5 text-emerald-400" />
                FlightGuard AI Email Template
              </DialogTitle>
              <DialogDescription className="mt-1.5 text-zinc-400">
                Live preview of the automated dispatch template for {payload.passengerName}.
              </DialogDescription>
            </div>
            <span className="rounded-full bg-zinc-800/80 px-3 py-1 text-xs font-semibold text-zinc-300 border border-zinc-700">
              Tier: {payload.tier}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-[80px_1fr] gap-2 text-sm bg-zinc-950/50 p-3 rounded-lg border border-zinc-800/80">
            <div className="text-zinc-500 font-medium">To:</div>
            <div className="text-zinc-200">{payload.passengerName} &lt;{payload.passengerEmail}&gt;</div>
            
            <div className="text-zinc-500 font-medium">Subject:</div>
            <div className="text-zinc-200 font-semibold">{payload.subject}</div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-auto p-6 bg-[#f4f4f5]">
          <div className="mx-auto shadow-sm rounded-xl overflow-hidden border border-zinc-200 bg-white">
            <iframe 
              srcDoc={payload.bodyHtml} 
              className="w-full min-h-[500px]" 
              title="Email Preview"
              style={{ border: 'none' }}
            />
          </div>
        </div>

        <div className="p-4 border-t border-zinc-800/60 bg-zinc-900/50 flex items-center justify-end gap-3">
          <Button 
            variant="outline" 
            onClick={handleCopyHtml}
            className="border-zinc-700 bg-zinc-800/50 hover:bg-zinc-800 hover:text-zinc-100 text-zinc-300 transition-all"
          >
            {copied ? <Check className="h-4 w-4 mr-2 text-emerald-400" /> : <Copy className="h-4 w-4 mr-2" />}
            {copied ? "Copied" : "Copy HTML"}
          </Button>
          
          <Button 
            onClick={handleOpenMailClient}
            className="bg-emerald-600 hover:bg-emerald-500 text-white transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_20px_rgba(16,185,129,0.5)]"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Open in Mail Client
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

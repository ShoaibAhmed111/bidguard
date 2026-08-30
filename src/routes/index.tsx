import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  ShieldAlert,
  Upload,
  XCircle,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  component: Index,
});

const API_BASE_URL =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "http://localhost:8001/api/v1";

const DEFAULT_TENDER_ID = "GEM-2026-CPCL-001";
const DEFAULT_MIN_LOCAL_CONTENT = 50;

type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
type ClauseStatus = "PASS" | "FAIL" | "WARNING";

interface ClauseAuditResult {
  clause_id: string;
  clause_title: string;
  is_mandatory: boolean;
  status: ClauseStatus;
  extracted_value: string | null;
  expected_value: string | null;
  discrepancy_notes: string | null;
  risk_penalty: number;
}

interface BidComplianceReport {
  tender_id: string;
  bidder_name: string;
  compliance_score: number;
  risk_tier: RiskTier;
  is_debarred: boolean;
  evaluated_at: string;
  clause_results: ClauseAuditResult[];
  executive_summary: string;
  recommended_action: string;
}

const RISK_STYLES: Record<RiskTier, string> = {
  LOW: "border-emerald-300 bg-emerald-100 text-emerald-800",
  MEDIUM: "border-amber-300 bg-amber-100 text-amber-900",
  HIGH: "border-red-300 bg-red-100 text-red-800",
  CRITICAL: "border-red-500 bg-red-600 text-white",
};

const SCORE_BAR_STYLES: Record<RiskTier, string> = {
  LOW: "[&>div]:bg-emerald-600",
  MEDIUM: "[&>div]:bg-amber-500",
  HIGH: "[&>div]:bg-red-600",
  CRITICAL: "[&>div]:bg-red-700",
};

const STATUS_STYLES: Record<ClauseStatus, string> = {
  PASS: "border-emerald-300 bg-emerald-100 text-emerald-800",
  WARNING: "border-amber-300 bg-amber-100 text-amber-900",
  FAIL: "border-red-300 bg-red-100 text-red-800",
};

function StatusIcon({ status }: { status: ClauseStatus }) {
  if (status === "PASS") return <CheckCircle2 className="size-4 text-emerald-600" />;
  if (status === "WARNING") return <AlertTriangle className="size-4 text-amber-600" />;
  return <XCircle className="size-4 text-red-600" />;
}

function formatEvaluatedAt(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

async function evaluateBid(
  file: File,
  tenderId: string,
  minLocalContentPct: number,
): Promise<BidComplianceReport> {
  const body = new FormData();
  body.append("file", file);
  body.append("tender_id", tenderId);
  body.append("min_local_content_pct", String(minLocalContentPct));

  const response = await fetch(`${API_BASE_URL}/tenders/evaluate`, { method: "POST", body });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Evaluation failed with status ${response.status}`;
    throw new Error(detail);
  }
  return (await response.json()) as BidComplianceReport;
}

function Index() {
  const [file, setFile] = React.useState<File | null>(null);
  const [tenderId, setTenderId] = React.useState(DEFAULT_TENDER_ID);
  const [minLocalContentPct, setMinLocalContentPct] = React.useState(DEFAULT_MIN_LOCAL_CONTENT);
  const [isDragging, setIsDragging] = React.useState(false);
  const [isEvaluating, setIsEvaluating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [report, setReport] = React.useState<BidComplianceReport | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF bid documents are supported.");
      return;
    }
    setError(null);
    setFile(candidate);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Attach a bid PDF before running the audit.");
      return;
    }
    setIsEvaluating(true);
    setError(null);
    try {
      setReport(await evaluateBid(file, tenderId, minLocalContentPct));
    } catch (cause) {
      setReport(null);
      setError(cause instanceof Error ? cause.message : "Unexpected error during evaluation.");
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">
              BidGuard AI — GeM Bid Compliance Platform
            </h1>
            <p className="text-sm text-muted-foreground">
              SIH26100 · automated statutory &amp; tender-criteria audit for procurement officers
            </p>
          </div>
          <Badge
            variant="outline"
            className="w-fit gap-1.5 border-amber-300 bg-amber-50 text-amber-900"
          >
            <ShieldAlert className="size-3.5" />
            Sandbox environment
          </Badge>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Upload bid document</CardTitle>
            <CardDescription>
              PDF bid submissions are parsed and audited clause by clause.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div
                role="button"
                tabIndex={0}
                aria-label="Drag and drop a bid PDF or browse"
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={cn(
                  "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
                  isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25",
                )}
              >
                {file ? (
                  <>
                    <FileText className="size-6 text-primary" />
                    <span className="text-sm font-medium break-all">{file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(0)} KB · click to replace
                    </span>
                  </>
                ) : (
                  <>
                    <Upload className="size-6 text-muted-foreground" />
                    <span className="text-sm font-medium">Drag &amp; drop the bid PDF here</span>
                    <span className="text-xs text-muted-foreground">or click to browse</span>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(event) => selectFile(event.target.files?.[0])}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tender-id">Tender ID</Label>
                <Input
                  id="tender-id"
                  value={tenderId}
                  onChange={(event) => setTenderId(event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="min-local-content">Minimum local content (%)</Label>
                <Input
                  id="min-local-content"
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={minLocalContentPct}
                  onChange={(event) => setMinLocalContentPct(Number(event.target.value))}
                />
              </div>

              <Button type="submit" className="w-full" disabled={isEvaluating}>
                {isEvaluating ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Analysing document…
                  </>
                ) : (
                  "Run compliance audit"
                )}
              </Button>
            </form>

            {error ? (
              <Alert variant="destructive" className="mt-4">
                <AlertTriangle className="size-4" />
                <AlertTitle>Evaluation failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>

        <section className="space-y-6">
          {isEvaluating ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-sm">Extracting clauses and verifying against GeM registries…</p>
              </CardContent>
            </Card>
          ) : null}

          {!isEvaluating && !report ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
                <FileText className="size-8" />
                <p className="text-sm">Upload a bid PDF to generate a compliance report.</p>
              </CardContent>
            </Card>
          ) : null}

          {!isEvaluating && report ? <ReportPanel report={report} /> : null}
        </section>
      </main>
    </div>
  );
}

function ReportPanel({ report }: { report: BidComplianceReport }) {
  return (
    <>
      <Card>
        <CardHeader className="gap-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>{report.bidder_name}</CardTitle>
              <CardDescription>
                Tender {report.tender_id} · evaluated {formatEvaluatedAt(report.evaluated_at)}
              </CardDescription>
            </div>
            <Badge className={cn("text-sm", RISK_STYLES[report.risk_tier])}>
              {report.risk_tier} RISK
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-muted-foreground">Compliance score</span>
              <span className="text-2xl font-semibold">{report.compliance_score.toFixed(1)}</span>
            </div>
            <Progress
              value={report.compliance_score}
              className={cn("h-3", SCORE_BAR_STYLES[report.risk_tier])}
            />
          </div>

          {report.is_debarred ? (
            <Alert variant="destructive">
              <ShieldAlert className="size-4" />
              <AlertTitle>Bidder is debarred</AlertTitle>
              <AlertDescription>
                This bidder appears in the debarment registry. Do not award without Vigilance
                clearance.
              </AlertDescription>
            </Alert>
          ) : null}

          <Alert>
            <CheckCircle2 className="size-4" />
            <AlertTitle>Recommended action</AlertTitle>
            <AlertDescription>{report.recommended_action}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      <Tabs defaultValue="clauses">
        <TabsList>
          <TabsTrigger value="clauses">Clause audit ({report.clause_results.length})</TabsTrigger>
          <TabsTrigger value="summary">Executive summary</TabsTrigger>
        </TabsList>

        <TabsContent value="clauses">
          <Card>
            <CardContent className="overflow-x-auto p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Clause</TableHead>
                    <TableHead>Extracted</TableHead>
                    <TableHead>Expected</TableHead>
                    <TableHead className="text-right">Penalty</TableHead>
                    <TableHead>Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.clause_results.map((clause) => (
                    <TableRow key={clause.clause_id}>
                      <TableCell>
                        <Badge className={cn("gap-1.5", STATUS_STYLES[clause.status])}>
                          <StatusIcon status={clause.status} />
                          {clause.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">
                        {clause.clause_title}
                        <div className="text-xs text-muted-foreground">
                          {clause.clause_id} · {clause.is_mandatory ? "mandatory" : "optional"}
                        </div>
                      </TableCell>
                      <TableCell>{clause.extracted_value ?? "—"}</TableCell>
                      <TableCell>{clause.expected_value ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {clause.risk_penalty.toFixed(1)}
                      </TableCell>
                      <TableCell className="max-w-sm text-sm text-muted-foreground">
                        {clause.discrepancy_notes ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="summary">
          <Card>
            <CardHeader>
              <CardTitle>Executive summary</CardTitle>
            </CardHeader>
            <CardContent className="text-sm whitespace-pre-line">
              {report.executive_summary}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}

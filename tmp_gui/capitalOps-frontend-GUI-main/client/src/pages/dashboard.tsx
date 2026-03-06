import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  FolderKanban,
  DollarSign,
  Users,
  AlertTriangle,
  ClipboardList,
  Handshake,
  TrendingUp,
  ArrowRight,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/stat-card";
import { PageHeader } from "@/components/page-header";
import { formatCurrency, getStatusColor, formatDate } from "@/lib/formatters";
import { Link } from "wouter";
import type { Deal, Project, RiskFlag, Allocation, Investor } from "@shared/schema";

export default function Dashboard() {
  const { data: backendStatus } = useQuery<{
    connected: boolean;
    url: string | null;
    mode: string;
  }>({ queryKey: ["/api/backend-status"] });

  const { data: stats, isLoading: statsLoading } = useQuery<{
    totalAssets: number;
    activeProjects: number;
    totalCapitalRequired: number;
    totalCapitalRaised: number;
    activeDeals: number;
    totalInvestors: number;
    openWorkOrders: number;
    riskFlags: number;
  }>({ queryKey: ["/api/dashboard/stats"] });

  const { data: deals } = useQuery<Deal[]>({ queryKey: ["/api/deals"] });
  const { data: projects } = useQuery<Project[]>({ queryKey: ["/api/projects"] });
  const { data: riskFlags } = useQuery<RiskFlag[]>({ queryKey: ["/api/risk-flags"] });
  const { data: allocations } = useQuery<Allocation[]>({ queryKey: ["/api/allocations"] });
  const { data: investors } = useQuery<Investor[]>({ queryKey: ["/api/investors"] });

  if (statsLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  const capitalProgress = stats && stats.totalCapitalRequired > 0
    ? Math.round((stats.totalCapitalRaised / stats.totalCapitalRequired) * 100)
    : 0;

  const getInvestorName = (id: string) => investors?.find(i => i.id === id)?.name || "Unknown";

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Portfolio Overview"
        description="Coral Capital Portfolio performance and operations summary"
      >
        {backendStatus && (
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium ${
            backendStatus.connected
              ? "bg-chart-2/15 text-chart-2"
              : "bg-chart-3/15 text-chart-3"
          }`} data-testid="text-backend-status">
            {backendStatus.connected ? (
              <><Wifi className="h-3 w-3" /> Backend Connected</>
            ) : (
              <><WifiOff className="h-3 w-3" /> Local Mode</>
            )}
          </div>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Assets"
          value={stats?.totalAssets || 0}
          icon={Building2}
          testId="stat-assets"
        />
        <StatCard
          title="Active Projects"
          value={stats?.activeProjects || 0}
          icon={FolderKanban}
          testId="stat-projects"
        />
        <StatCard
          title="Capital Raised"
          value={formatCurrency(stats?.totalCapitalRaised || 0)}
          subtitle={`of ${formatCurrency(stats?.totalCapitalRequired || 0)} required`}
          icon={DollarSign}
          testId="stat-capital"
        />
        <StatCard
          title="Active Investors"
          value={stats?.totalInvestors || 0}
          icon={Users}
          testId="stat-investors"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between gap-1 space-y-0 pb-4">
            <CardTitle className="text-sm font-semibold">Capital Pipeline</CardTitle>
            <Link href="/deals" data-testid="link-view-deals">
              <span className="text-xs text-primary flex items-center gap-1 cursor-pointer">
                View All <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            {deals?.map((deal) => {
              const project = projects?.find(p => p.id === deal.projectId);
              const progress = deal.capitalRequired > 0 ? Math.round((deal.capitalRaised / deal.capitalRequired) * 100) : 0;
              return (
                <div key={deal.id} className="space-y-2 p-3 rounded-md bg-accent/30" data-testid={`deal-row-${deal.id}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Handshake className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm font-medium truncate">{project?.phase || "Unknown"}</span>
                      <Badge variant="secondary" className={getStatusColor(deal.status)}>
                        {deal.status}
                      </Badge>
                    </div>
                    <span className="text-sm font-semibold shrink-0">{formatCurrency(deal.capitalRaised)} / {formatCurrency(deal.capitalRequired)}</span>
                  </div>
                  <Progress value={progress} className="h-1.5" />
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>{deal.returnProfile}</span>
                    <span>{deal.duration} | {deal.riskLevel} Risk</span>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-1 space-y-0 pb-4">
            <CardTitle className="text-sm font-semibold">Risk Alerts</CardTitle>
            <Badge variant="secondary" className="bg-destructive/15 text-destructive">
              {stats?.riskFlags || 0} Open
            </Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {riskFlags?.filter(r => r.status === "Open").map((flag) => {
              const project = projects?.find(p => p.id === flag.projectId);
              return (
                <div key={flag.id} className="p-3 rounded-md bg-accent/30 space-y-1" data-testid={`risk-flag-${flag.id}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <AlertTriangle className={`h-3.5 w-3.5 shrink-0 ${flag.severity === "High" ? "text-chart-5" : "text-chart-3"}`} />
                      <span className="text-xs font-medium">{flag.category}</span>
                    </div>
                    <Badge variant="secondary" className={getStatusColor(flag.severity)}>
                      {flag.severity}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">{flag.description}</p>
                  <p className="text-[10px] text-muted-foreground/70">{project?.phase} | {formatDate(flag.createdAt)}</p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-1 space-y-0 pb-4">
            <CardTitle className="text-sm font-semibold">Recent Allocations</CardTitle>
            <Link href="/allocations" data-testid="link-view-allocations">
              <span className="text-xs text-primary flex items-center gap-1 cursor-pointer">
                View All <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {allocations?.slice(0, 4).map((alloc) => (
              <div key={alloc.id} className="flex items-center justify-between gap-3 p-3 rounded-md bg-accent/30" data-testid={`allocation-row-${alloc.id}`}>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{getInvestorName(alloc.investorId)}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(alloc.softCommitAmount)} soft | {formatCurrency(alloc.hardCommitAmount)} hard
                  </p>
                </div>
                <Badge variant="secondary" className={getStatusColor(alloc.status)}>
                  {alloc.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-1 space-y-0 pb-4">
            <CardTitle className="text-sm font-semibold">Execution Summary</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                <ClipboardList className="h-3 w-3 mr-1" />
                {stats?.openWorkOrders || 0} Open WOs
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {projects?.map((project) => {
              const budgetUsed = project.budgetTotal > 0 ? Math.round((project.budgetActual / project.budgetTotal) * 100) : 0;
              return (
                <div key={project.id} className="p-3 rounded-md bg-accent/30 space-y-2" data-testid={`project-summary-${project.id}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <FolderKanban className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm font-medium truncate">{project.phase}</span>
                    </div>
                    <Badge variant="secondary" className={getStatusColor(project.status)}>
                      {project.status}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span>Budget: {formatCurrency(project.budgetActual)} / {formatCurrency(project.budgetTotal)}</span>
                      <span>{budgetUsed}%</span>
                    </div>
                    <Progress value={budgetUsed} className="h-1.5" />
                  </div>
                  <p className="text-[10px] text-muted-foreground/70">PM: {project.pmAssigned} | Target: {formatDate(project.targetCompletion)}</p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Deals"
          value={stats?.activeDeals || 0}
          icon={Handshake}
          testId="stat-active-deals"
        />
        <StatCard
          title="Capital Progress"
          value={`${capitalProgress}%`}
          subtitle="Overall portfolio"
          icon={TrendingUp}
          testId="stat-capital-progress"
        />
        <StatCard
          title="Open Work Orders"
          value={stats?.openWorkOrders || 0}
          icon={ClipboardList}
          testId="stat-work-orders"
        />
        <StatCard
          title="Risk Flags"
          value={stats?.riskFlags || 0}
          icon={AlertTriangle}
          testId="stat-risk-flags"
        />
      </div>
    </div>
  );
}

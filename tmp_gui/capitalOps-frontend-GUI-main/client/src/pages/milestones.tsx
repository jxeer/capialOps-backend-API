import { useQuery } from "@tanstack/react-query";
import { Milestone as MilestoneIcon, Calendar, AlertTriangle, CheckCircle2, Clock, Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { formatDate, getStatusColor } from "@/lib/formatters";
import type { Milestone, Project, Asset } from "@shared/schema";

function MilestoneStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "Completed":
      return <CheckCircle2 className="h-4 w-4 text-chart-2" />;
    case "In Progress":
      return <Clock className="h-4 w-4 text-chart-1" />;
    case "Delayed":
      return <AlertTriangle className="h-4 w-4 text-destructive" />;
    default:
      return <Circle className="h-4 w-4 text-muted-foreground" />;
  }
}

export default function Milestones() {
  const { data: milestones, isLoading } = useQuery<Milestone[]>({ queryKey: ["/api/milestones"] });
  const { data: projects } = useQuery<Project[]>({ queryKey: ["/api/projects"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-48" />)}
        </div>
      </div>
    );
  }

  const groupedByProject = projects?.map((project) => ({
    project,
    asset: assets?.find(a => a.id === project.assetId),
    milestones: milestones?.filter(m => m.projectId === project.id) || [],
  })) || [];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Milestones"
        description="Project milestone tracking and progress monitoring"
      />

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5 text-chart-2" /> Completed
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5 text-chart-1" /> In Progress
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Circle className="h-3.5 w-3.5 text-muted-foreground" /> Pending
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <AlertTriangle className="h-3.5 w-3.5 text-destructive" /> Delayed
        </div>
      </div>

      <div className="space-y-4">
        {groupedByProject.map(({ project, asset, milestones: projectMilestones }) => (
          <Card key={project.id} data-testid={`card-milestones-${project.id}`}>
            <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0 pb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10">
                  <MilestoneIcon className="h-4 w-4 text-primary" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-sm truncate">{asset?.name || "Unknown"}</CardTitle>
                  <p className="text-xs text-muted-foreground">{project.phase}</p>
                </div>
              </div>
              <Badge variant="secondary">
                {projectMilestones.filter(m => m.status === "Completed").length}/{projectMilestones.length}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {projectMilestones.map((ms, index) => (
                  <div
                    key={ms.id}
                    className="flex items-start gap-3"
                    data-testid={`milestone-row-${ms.id}`}
                  >
                    <div className="flex flex-col items-center gap-1 pt-0.5">
                      <MilestoneStatusIcon status={ms.status} />
                      {index < projectMilestones.length - 1 && (
                        <div className="w-px h-8 bg-border" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0 pb-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-sm font-medium truncate">{ms.name}</span>
                          {ms.riskFlag && (
                            <AlertTriangle className="h-3.5 w-3.5 text-chart-5 shrink-0" />
                          )}
                        </div>
                        <Badge variant="secondary" className={getStatusColor(ms.status)}>
                          {ms.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Target: {formatDate(ms.targetDate)}
                        </span>
                        {ms.completionDate && (
                          <span>Completed: {formatDate(ms.completionDate)}</span>
                        )}
                        <Badge variant="secondary" className="text-[10px]">{ms.category}</Badge>
                      </div>
                      {ms.delayExplanation && (
                        <p className="text-xs text-chart-5 mt-1">{ms.delayExplanation}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

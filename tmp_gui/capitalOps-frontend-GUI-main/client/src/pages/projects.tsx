import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Calendar, User, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { formatCurrency, formatDate, getStatusColor } from "@/lib/formatters";
import type { Project, Asset, Milestone } from "@shared/schema";

export default function Projects() {
  const { data: projects, isLoading } = useQuery<Project[]>({ queryKey: ["/api/projects"] });
  const { data: assets } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });
  const { data: milestones } = useQuery<Milestone[]>({ queryKey: ["/api/milestones"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-64" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Projects"
        description="Active development projects and execution tracking"
      />

      <div className="space-y-4">
        {projects?.map((project) => {
          const asset = assets?.find(a => a.id === project.assetId);
          const projectMilestones = milestones?.filter(m => m.projectId === project.id) || [];
          const completedMilestones = projectMilestones.filter(m => m.status === "Completed").length;
          const milestoneProgress = projectMilestones.length > 0
            ? Math.round((completedMilestones / projectMilestones.length) * 100)
            : 0;
          const budgetProgress = project.budgetTotal > 0 ? Math.round((project.budgetActual / project.budgetTotal) * 100) : 0;
          const riskMilestones = projectMilestones.filter(m => m.riskFlag);

          return (
            <Card key={project.id} data-testid={`card-project-${project.id}`}>
              <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                    <FolderKanban className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <CardTitle className="text-base truncate">{asset?.name || "Unknown Asset"}</CardTitle>
                    <p className="text-xs text-muted-foreground">{project.phase} | {asset?.location}</p>
                  </div>
                </div>
                <Badge variant="secondary" className={getStatusColor(project.status)}>
                  {project.status}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Budget</p>
                    <p className="text-sm font-semibold">{formatCurrency(project.budgetActual)}</p>
                    <p className="text-[10px] text-muted-foreground">of {formatCurrency(project.budgetTotal)}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Timeline</p>
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-muted-foreground" />
                      <p className="text-sm font-medium">{formatDate(project.targetCompletion)}</p>
                    </div>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">PM Assigned</p>
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 text-muted-foreground" />
                      <p className="text-sm font-medium">{project.pmAssigned}</p>
                    </div>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Risk Flags</p>
                    <div className="flex items-center gap-1">
                      <AlertTriangle className={`h-3 w-3 ${riskMilestones.length > 0 ? "text-chart-5" : "text-muted-foreground"}`} />
                      <p className="text-sm font-medium">{riskMilestones.length}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-muted-foreground">Budget Usage</span>
                    <span className="font-medium">{budgetProgress}%</span>
                  </div>
                  <Progress value={budgetProgress} className="h-1.5" />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-muted-foreground">Milestone Progress ({completedMilestones}/{projectMilestones.length})</span>
                    <span className="font-medium">{milestoneProgress}%</span>
                  </div>
                  <Progress value={milestoneProgress} className="h-1.5" />
                </div>

                {projectMilestones.length > 0 && (
                  <div className="pt-3 border-t border-border">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Milestones</p>
                    <div className="flex flex-wrap gap-2">
                      {projectMilestones.map((ms) => (
                        <Badge
                          key={ms.id}
                          variant="secondary"
                          className={getStatusColor(ms.status)}
                        >
                          {ms.riskFlag && <AlertTriangle className="h-3 w-3 mr-1" />}
                          {ms.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

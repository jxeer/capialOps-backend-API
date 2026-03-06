import { useQuery } from "@tanstack/react-query";
import { Building2, MapPin, Maximize2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { getStatusColor, formatNumber } from "@/lib/formatters";
import type { Asset } from "@shared/schema";

export default function Assets() {
  const { data: assets, isLoading } = useQuery<Asset[]>({ queryKey: ["/api/assets"] });

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-44" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Assets"
        description="Portfolio asset management and health overview"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {assets?.map((asset) => (
          <Card key={asset.id} className="hover-elevate" data-testid={`card-asset-${asset.id}`}>
            <CardContent className="p-5 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                    <Building2 className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold truncate" data-testid={`text-asset-name-${asset.id}`}>{asset.name}</h3>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0" />
                      <span>{asset.location}</span>
                    </div>
                  </div>
                </div>
                <Badge variant="secondary" className={getStatusColor(asset.status)}>
                  {asset.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-0.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Type</p>
                  <p className="text-sm font-medium">{asset.assetType}</p>
                </div>
                <div className="space-y-0.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Square Footage</p>
                  <div className="flex items-center gap-1">
                    <Maximize2 className="h-3 w-3 text-muted-foreground" />
                    <p className="text-sm font-medium">{formatNumber(asset.squareFootage)} SF</p>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  Asset Manager: <span className="text-foreground font-medium">{asset.assetManager}</span>
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

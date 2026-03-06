import { useLocation, Link } from "wouter";
import {
  LayoutDashboard,
  Building2,
  FolderKanban,
  Handshake,
  Users,
  Milestone,
  Truck,
  ClipboardList,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";

const capitalEngineItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Deals", url: "/deals", icon: Handshake },
  { title: "Investors", url: "/investors", icon: Users },
  { title: "Allocations", url: "/allocations", icon: TrendingUp },
];

const executionItems = [
  { title: "Projects", url: "/projects", icon: FolderKanban },
  { title: "Milestones", url: "/milestones", icon: Milestone },
  { title: "Risk Flags", url: "/risk-flags", icon: AlertTriangle },
];

const assetVendorItems = [
  { title: "Assets", url: "/assets", icon: Building2 },
  { title: "Vendors", url: "/vendors", icon: Truck },
  { title: "Work Orders", url: "/work-orders", icon: ClipboardList },
];

export function AppSidebar() {
  const [location] = useLocation();

  const renderGroup = (label: string, items: typeof capitalEngineItems) => (
    <SidebarGroup>
      <SidebarGroupLabel className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/70">
        {label}
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                asChild
                data-active={location === item.url}
                className="data-[active=true]:bg-sidebar-accent data-[active=true]:text-sidebar-accent-foreground"
              >
                <Link href={item.url} data-testid={`nav-${item.title.toLowerCase().replace(/\s+/g, "-")}`}>
                  <item.icon className="h-4 w-4" />
                  <span>{item.title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight" data-testid="text-app-title">CapitalOps</h2>
            <p className="text-[10px] text-muted-foreground">Built on Coral8</p>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {renderGroup("Capital Engine", capitalEngineItems)}
        {renderGroup("Execution Control", executionItems)}
        {renderGroup("Asset & Vendor", assetVendorItems)}
      </SidebarContent>
      <SidebarFooter className="p-4">
        <div className="rounded-md bg-accent/50 p-3">
          <p className="text-xs font-medium text-muted-foreground">Coral Capital Portfolio</p>
          <p className="text-[10px] text-muted-foreground/70">3 Active Projects</p>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { AppShell, PublicLayout } from "./components/Layouts";
import { GuestOnly, RequireAuth } from "./components/Guards";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { ComplaintDetailPage, ComplaintNewPage, ComplaintsListPage } from "./pages/Complaints";
import {
  AboutPage,
  AccessDenied,
  DirectoryPage,
  EmergencyPage,
  FeedbackPage,
  GenericList,
  OverviewPage,
  ProfilePage,
  ReelsPage,
} from "./pages/CivicPages";
import { AdminUsersPage, AuditPage, CreateProjectButton, MapPage, RolesPage } from "./pages/AdminPages";

function ProjectsAppPage() {
  return (
    <>
      <CreateProjectButton />
      <GenericList path="/api/v1/projects" title="Projects" />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/projects" element={<GenericList path="/api/v1/projects?public_only=true" title="Public projects" />} />
            <Route path="/announcements" element={<GenericList path="/api/v1/announcements" title="Announcements" />} />
            <Route path="/reels" element={<ReelsPage />} />
            <Route path="/emergency" element={<EmergencyPage />} />
            <Route path="/directory" element={<DirectoryPage />} />
            <Route path="/cleaning" element={<GenericList path="/api/v1/cleaning" title="Cleaning schedules" />} />
            <Route element={<GuestOnly />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/app" element={<OverviewPage />} />
              <Route path="/app/complaints" element={<ComplaintsListPage />} />
              <Route path="/app/complaints/new" element={<ComplaintNewPage />} />
              <Route path="/app/complaints/:id" element={<ComplaintDetailPage />} />
              <Route path="/app/projects" element={<ProjectsAppPage />} />
              <Route path="/app/reels" element={<ReelsPage />} />
              <Route path="/app/announcements" element={<GenericList path="/api/v1/announcements" title="Announcements" />} />
              <Route path="/app/feedback" element={<FeedbackPage />} />
              <Route path="/app/emergency" element={<EmergencyPage />} />
              <Route path="/app/cleaning" element={<GenericList path="/api/v1/cleaning" title="Cleaning" />} />
              <Route path="/app/directory" element={<DirectoryPage />} />
              <Route path="/app/profile" element={<ProfilePage />} />
              <Route path="/app/analytics" element={<OverviewPage />} />
              <Route path="/app/map" element={<MapPage />} />
              <Route path="/app/nearby" element={<ComplaintsListPage />} />
              <Route element={<RequireAuth roles={["OFFICER", "ADMIN"]} />}>
                <Route path="/app/evidence" element={<ComplaintsListPage />} />
              </Route>
              <Route element={<RequireAuth roles={["NAGAR_SEVAK"]} />}>
                <Route path="/app/ward" element={<OverviewPage />} />
              </Route>
              <Route element={<RequireAuth roles={["OFFICER"]} />}>
                <Route path="/app/officer" element={<OverviewPage />} />
              </Route>
              <Route element={<RequireAuth roles={["ENGINEER"]} />}>
                <Route path="/app/engineer" element={<OverviewPage />} />
              </Route>
              <Route element={<RequireAuth roles={["CONTRACTOR"]} />}>
                <Route path="/app/contractor" element={<OverviewPage />} />
              </Route>
              <Route element={<RequireAuth roles={["ADMIN"]} />}>
                <Route path="/app/admin" element={<OverviewPage />} />
                <Route path="/app/admin/users" element={<AdminUsersPage />} />
                <Route path="/app/admin/roles" element={<RolesPage />} />
                <Route path="/app/admin/audit" element={<AuditPage />} />
              </Route>
            </Route>
          </Route>
          <Route path="/denied" element={<AccessDenied />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

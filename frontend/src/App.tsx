import { Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { ApplyPage } from "@/pages/ApplyPage";
import { AutoRunPage } from "@/pages/AutoRunPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { JobDetailPage } from "@/pages/JobDetailPage";
import { JobsPage } from "@/pages/JobsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { TailorPage } from "@/pages/TailorPage";
import { TrackerPage } from "@/pages/TrackerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="jobs/:id/apply" element={<ApplyPage />} />
        <Route path="jobs/:id/tailor" element={<TailorPage />} />
        <Route path="auto-run/:id" element={<AutoRunPage />} />
        <Route path="tracker" element={<TrackerPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

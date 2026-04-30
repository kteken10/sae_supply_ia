import { Routes, Route } from "react-router-dom";
import { DashboardLayout } from "./layouts/DashboardLayout";
import DashboardPage from "./pages/DashboardPage";
import ForecastPage from "./pages/ForecastPage";
import SuppliersPage from "./pages/SuppliersPage";
import AuditPage from "./pages/AuditPage";

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="forecast" element={<ForecastPage />} />
        <Route path="suppliers" element={<SuppliersPage />} />
        <Route path="audit" element={<AuditPage />} />
      </Route>
    </Routes>
  );
}

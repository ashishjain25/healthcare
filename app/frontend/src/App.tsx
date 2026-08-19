import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { PatientDashboard } from "./pages/PatientDashboard";
import { DoctorDashboard } from "./pages/DoctorDashboard";
import { RadiologistDashboard } from "./pages/RadiologistDashboard";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (user) return <Navigate to={`/${user.role}`} replace />;
  return <Navigate to="/login" replace />;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/patient"
        element={
          <ProtectedRoute role="patient">
            <PatientDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor"
        element={
          <ProtectedRoute role="doctor">
            <DoctorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/radiologist"
        element={
          <ProtectedRoute role="radiologist">
            <RadiologistDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

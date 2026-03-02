import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import ToolList from './pages/ToolList';
import ToolDetail from './pages/ToolDetail';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Register from './pages/Register';
import { useAuthStore } from './stores/useAuthStore';

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/tools" element={<RequireAuth><Layout><ToolList /></Layout></RequireAuth>} />
        <Route path="/tools/:slug" element={<RequireAuth><Layout><ToolDetail /></Layout></RequireAuth>} />
        <Route path="/projects" element={<RequireAuth><Layout><Projects /></Layout></RequireAuth>} />
        <Route path="/projects/:id" element={<RequireAuth><Layout><ProjectDetail /></Layout></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><Layout><Profile /></Layout></RequireAuth>} />
      </Routes>
    </Router>
  );
};

export default App;

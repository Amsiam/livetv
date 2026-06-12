import { Navigate, Route, Routes } from 'react-router-dom';
import { AppHeader } from './components/AppHeader';
import { HomePage } from './pages/HomePage';
import { MatchesPage } from './pages/MatchesPage';
import { MatchWatchPage } from './pages/MatchWatchPage';
import { WatchPage } from './pages/WatchPage';

export default function App() {
  return (
    <div className="app-shell">
      <AppHeader />
      <Routes>
        <Route path="/" element={<MatchesPage />} />
        <Route path="/matches/:matchId" element={<MatchWatchPage />} />
        <Route path="/tv" element={<HomePage />} />
        <Route path="/watch/:channelId" element={<WatchPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

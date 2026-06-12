import { NavLink, useLocation } from 'react-router-dom';

export function AppHeader() {
  const { pathname } = useLocation();
  const matchesActive = pathname === '/' || pathname.startsWith('/matches/');

  return (
    <header className="app-header">
      <NavLink to="/" className="brand">
        <span className="brand-mark" aria-hidden />
        <span>
          Live TV
          <small>Watch in your browser</small>
        </span>
      </NavLink>
      <nav className="main-nav" aria-label="Main">
        <NavLink to="/" className={() => `nav-link${matchesActive ? ' active' : ''}`}>
          Matches
        </NavLink>
        <NavLink
          to="/tv"
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          TV
        </NavLink>
      </nav>
    </header>
  );
}

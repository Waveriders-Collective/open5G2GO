import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Network, Activity } from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { path: '/subscribers', label: 'Devices', icon: <Users className="w-5 h-5" /> },
  { path: '/network', label: 'Network Config', icon: <Network className="w-5 h-5" /> },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();

  return (
    <aside className="bg-gray-charcoal text-white w-64 min-h-screen shadow-xl">
      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center space-x-3 px-4 py-3 rounded-lg font-body
                transition-colors duration-200
                ${
                  isActive
                    ? 'bg-primary text-white'
                    : 'text-gray-300 hover:bg-gray-dark hover:text-white'
                }
              `}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 mt-8 border-t border-gray-dark">
        <div className="flex items-center space-x-2 text-sm font-body text-gray-400">
          <Activity className="w-4 h-4" />
          <span>v0.1.0-beta</span>
        </div>
      </div>
    </aside>
  );
};

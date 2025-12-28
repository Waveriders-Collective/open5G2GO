import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, icon, trend, className = '' }) => {
  return (
    <div className={`bg-white rounded-lg shadow-md border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-body text-gray-medium">{title}</p>
          <p className="text-3xl font-heading text-gray-charcoal mt-2">{value}</p>
          {trend && (
            <p
              className={`text-sm font-body mt-2 ${
                trend.isPositive ? 'text-primary-deep' : 'text-red-600'
              }`}
            >
              {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        {icon && <div className="text-primary opacity-20 ml-4">{icon}</div>}
      </div>
    </div>
  );
};

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, className = '', title, subtitle, action }) => {
  return (
    <div className={`bg-white rounded-lg shadow-md border border-gray-200 ${className}`}>
      {(title || subtitle || action) && (
        <div className="px-6 py-4 border-b border-gray-200 flex items-start justify-between">
          <div>
            {title && <h3 className="font-heading text-lg text-gray-charcoal">{title}</h3>}
            {subtitle && <p className="text-sm text-gray-medium mt-1">{subtitle}</p>}
          </div>
          {action && <div className="ml-4">{action}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
};

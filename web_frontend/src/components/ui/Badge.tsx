// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2025 Waveriders Collective Inc.

import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'info' | 'error' | 'neutral';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', className = '' }) => {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-body';

  const variantStyles = {
    success: 'bg-primary-light text-primary-deep',
    warning: 'bg-accent-yellow/20 text-gray-charcoal',
    info: 'bg-blue-100 text-blue-800',
    error: 'bg-red-100 text-red-800',
    neutral: 'bg-gray-200 text-gray-dark',
  };

  return <span className={`${baseStyles} ${variantStyles[variant]} ${className}`}>{children}</span>;
};

import type { ReactNode } from 'react';
import { Card, CardBody } from './Card';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    label: string;
  };
  icon?: ReactNode;
  onClick?: () => void;
}

export const MetricCard = ({
  title,
  value,
  change,
  icon,
  onClick,
}: MetricCardProps) => {
  return (
    <Card hover={!!onClick} onClick={onClick}>
      <CardBody>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
            {change && (
              <p className="mt-2 text-sm text-gray-600">
                <span
                  className={
                    change.value >= 0 ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {change.value >= 0 ? '↑' : '↓'} {Math.abs(change.value)}
                </span>{' '}
                {change.label}
              </p>
            )}
          </div>
          {icon && <div className="text-gray-400">{icon}</div>}
        </div>
      </CardBody>
    </Card>
  );
};

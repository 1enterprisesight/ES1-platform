import { BellIcon, UserCircleIcon } from '@heroicons/react/24/outline';

interface TopBarProps {
  title: string;
}

export const TopBar = ({ title }: TopBarProps) => {
  return (
    <div className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200">
      <h2 className="text-2xl font-semibold text-gray-900">{title}</h2>

      <div className="flex items-center space-x-4">
        {/* Notifications */}
        <button className="relative p-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100">
          <BellIcon className="w-6 h-6" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        {/* User menu */}
        <button className="flex items-center space-x-2 text-gray-700 hover:text-gray-900">
          <UserCircleIcon className="w-8 h-8" />
          <span className="text-sm font-medium">Admin</span>
        </button>
      </div>
    </div>
  );
};

import { Loader } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
}

export default function LoadingSpinner({ 
  size = 'medium', 
  color = 'text-purple-600' 
}: LoadingSpinnerProps) {
  const sizeClasses = {
    small: 'h-4 w-4',
    medium: 'h-8 w-8',
    large: 'h-12 w-12',
  };
  
  return (
    <div className="flex items-center justify-center">
      <Loader className={`${sizeClasses[size]} ${color} animate-spin`} />
    </div>
  );
}
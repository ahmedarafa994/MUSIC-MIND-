import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_verified: boolean;
  subscription_tier: 'free' | 'premium' | 'pro';
  avatar_url?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'AUTH_FAILURE' }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: User };

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('token'),
  isLoading: false,
  isAuthenticated: false,
};

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'AUTH_START':
      return { ...state, isLoading: true };
    case 'AUTH_SUCCESS':
      return {
        ...state,
        isLoading: false,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
      };
    case 'AUTH_FAILURE':
      return {
        ...state,
        isLoading: false,
        isAuthenticated: false,
        user: null,
        token: null,
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null,
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: action.payload,
      };
    default:
      return state;
  }
};

interface AuthContextType {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => void;
  updateUser: (userData: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      // Verify token and get user data
      verifyToken(token);
    }
  }, []);

  const verifyToken = async (token: string) => {
    try {
      dispatch({ type: 'AUTH_START' });
      const response = await authAPI.getMe(token);
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user: response.data, token },
      });
    } catch (error) {
      localStorage.removeItem('token');
      dispatch({ type: 'AUTH_FAILURE' });
    }
  };

  const login = async (email: string, password: string) => {
    try {
      dispatch({ type: 'AUTH_START' });
      const response = await authAPI.login({ email, password });
      
      const { access_token, user } = response.data;
      localStorage.setItem('token', access_token);
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: { user, token: access_token },
      });
      
      toast.success('Login successful!');
    } catch (error: any) {
      dispatch({ type: 'AUTH_FAILURE' });
      toast.error(error.response?.data?.detail || 'Login failed');
      throw error;
    }
  };

  const register = async (userData: any) => {
    try {
      dispatch({ type: 'AUTH_START' });
      const response = await authAPI.register(userData);
      
      toast.success('Registration successful! Please check your email to verify your account.');
      dispatch({ type: 'AUTH_FAILURE' }); // Don't auto-login, require email verification
    } catch (error: any) {
      dispatch({ type: 'AUTH_FAILURE' });
      toast.error(error.response?.data?.detail || 'Registration failed');
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    dispatch({ type: 'LOGOUT' });
    toast.success('Logged out successfully');
  };

  const updateUser = (userData: User) => {
    dispatch({ type: 'UPDATE_USER', payload: userData });
  };

  const value = {
    state,
    login,
    register,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
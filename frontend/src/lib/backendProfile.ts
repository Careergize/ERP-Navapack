import type { LoginResponse } from './api';
import type { User } from '@/types';

export function backendProfile(data: NonNullable<LoginResponse['user']>): User {
  if (typeof data.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.id)
    || !Array.isArray(data.roles) || !data.roles.every(r=>typeof r==='string')
    || !Array.isArray(data.permissions) || !data.permissions.every(p=>typeof p==='string')) throw new Error('Invalid account profile.');
  return {id:data.id,name:data.name??data.email??'',role:'authenticated',roles:data.roles,
    permissions:data.permissions,backendSession:true};
}

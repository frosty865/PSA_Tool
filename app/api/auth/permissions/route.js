import { NextResponse } from 'next/server';
import { AuthService } from '../../../lib/auth-server';

export async function GET(request) {
  try {
    const token = request.cookies.get('auth-token')?.value;

    if (!token) {
      return NextResponse.json(
        { success: false, error: 'No authentication token' },
        { status: 401 }
      );
    }

    const result = await AuthService.verifyToken(token);

    if (!result.success) {
      return NextResponse.json(
        { success: false, error: result.error },
        { status: 401 }
      );
    }

    const permissions = AuthService.getUserPermissions(result.user.role);

    return NextResponse.json({
      success: true,
      permissions,
      user: result.user
    });

  } catch (error) {
    console.error('Permissions check error:', error);
    return NextResponse.json(
      { success: false, error: 'Permissions check failed' },
      { status: 500 }
    );
  }
}
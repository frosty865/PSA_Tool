import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const { sessionToken } = await request.json();

    if (!sessionToken) {
      return NextResponse.json(
        { success: false, error: 'Session token required' },
        { status: 400 }
      );
    }

    // For now, return a mock user (this should be replaced with real session validation)
    const user = {
      id: 'test-user-id',
      username: 'admin',
      full_name: 'Admin User',
      role: 'admin',
      organization: 'CISA'
    };

    return NextResponse.json({
      success: true,
      user: user
    });

  } catch (error) {
    console.error('Session validation error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

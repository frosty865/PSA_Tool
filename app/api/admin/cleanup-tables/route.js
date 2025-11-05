// Admin-only API route to execute DDL for table cleanup
import { NextResponse } from 'next/server';
import { requireAdmin } from '../../../../lib/auth-middleware';
import { createClient } from '@supabase/supabase-js';
import { Pool } from 'pg';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const databaseUrl = process.env.DATABASE_URL;

function authErrorResponse(error) {
  const msg = String(error || 'Unauthorized');
  const status = msg.includes('Authentication') ? 401 : 403;
  return NextResponse.json({ success: false, error: msg }, { status });
}

export async function POST(request) {
  const { user, error: authError } = await requireAdmin(request);
  if (authError) return authErrorResponse(authError);

  try {
    const body = await request.json();
    const { sql } = body;

    if (!sql || typeof sql !== 'string') {
      return NextResponse.json(
        { success: false, error: 'SQL query is required' },
        { status: 400 }
      );
    }

    // Only allow DROP TABLE commands for safety
    if (!sql.trim().toUpperCase().startsWith('DROP TABLE')) {
      return NextResponse.json(
        { success: false, error: 'Only DROP TABLE commands are allowed' },
        { status: 400 }
      );
    }

    if (!databaseUrl) {
      return NextResponse.json(
        { success: false, error: 'DATABASE_URL not configured. Cannot execute SQL directly.' },
        { status: 500 }
      );
    }

    // Execute SQL using direct Postgres connection
    const pool = new Pool({ connectionString: databaseUrl });
    try {
      const client = await pool.connect();
      try {
        await client.query(sql);
        return NextResponse.json({ success: true, message: 'SQL executed successfully' });
      } finally {
        client.release();
      }
    } finally {
      await pool.end();
    }
  } catch (error) {
    console.error('Error executing cleanup SQL:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}


import { NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/talents/RSC/613520`);
    const text = await res.text();
    return NextResponse.json({ status: res.status, text });
  } catch (err: any) {
    return NextResponse.json({ error: err.message });
  }
}

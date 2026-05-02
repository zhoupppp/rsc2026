import { NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/talents/RSC/613520`);
    const text = await res.text();
    return new NextResponse(`<html><body><pre>${text}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><pre>ERROR: ${err.message}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

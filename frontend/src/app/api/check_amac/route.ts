import { NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api';

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const id = (url.searchParams.get("id") || "").trim();
    if (!id) return new NextResponse(`<html><body><pre>Missing id. Use /api/check_amac?id=&lt;practitioner_id&gt;</pre></body></html>`, { headers: { 'Content-Type': 'text/html' } });

    const res = await fetch(`${API_BASE_URL}/api/talents/AMAC/${encodeURIComponent(id)}`);
    const text = await res.text();
    return new NextResponse(`<html><body><h1>API_RESULT ${id}</h1><p id="res">${text}</p></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><pre>ERROR: \n${err.message}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

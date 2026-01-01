import { NextResponse } from "next/server";
import { getBusinesses } from "@/lib/database";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const tierFilter = searchParams.get("tier");

    const businesses = await getBusinesses(tierFilter || undefined);
    return NextResponse.json(businesses);
  } catch (error) {
    console.error("Error fetching businesses:", error);
    return NextResponse.json(
      { error: "Failed to fetch businesses" },
      { status: 500 }
    );
  }
}

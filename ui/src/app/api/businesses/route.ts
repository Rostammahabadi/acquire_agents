import { NextResponse } from "next/server";
import { getBusinesses } from "@/lib/database";

export async function GET() {
  try {
    const businesses = await getBusinesses();
    return NextResponse.json(businesses);
  } catch (error) {
    console.error("Error fetching businesses:", error);
    return NextResponse.json(
      { error: "Failed to fetch businesses" },
      { status: 500 }
    );
  }
}

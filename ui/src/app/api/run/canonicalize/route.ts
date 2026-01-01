import { NextResponse } from "next/server";
import { triggerCanonicalization } from "@/lib/database";

export async function POST(request: Request) {
  try {
    const { business_id } = await request.json();

    if (!business_id) {
      return NextResponse.json(
        { error: "business_id is required" },
        { status: 400 }
      );
    }

    const result = await triggerCanonicalization(business_id);
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error triggering canonicalization:", error);
    return NextResponse.json(
      { error: "Failed to trigger canonicalization" },
      { status: 500 }
    );
  }
}

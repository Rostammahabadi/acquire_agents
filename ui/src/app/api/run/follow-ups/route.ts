import { NextResponse } from "next/server";
import { triggerFollowUpGeneration } from "@/lib/database";

export async function POST(request: Request) {
  try {
    const { business_id } = await request.json();

    if (!business_id) {
      return NextResponse.json(
        { error: "business_id is required" },
        { status: 400 }
      );
    }

    const result = await triggerFollowUpGeneration(business_id);
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error triggering follow-up generation:", error);
    return NextResponse.json(
      { error: "Failed to trigger follow-up generation" },
      { status: 500 }
    );
  }
}

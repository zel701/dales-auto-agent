import { InviteGate } from "@/components/invite-gate";
import { Wizard } from "@/components/wizard";
import { hasInvite } from "@/lib/invite-session";

export default async function Home() {
  // Reading the cookie opts this page into dynamic rendering, so the unlock
  // state is never served from a cache.
  const unlocked = await hasInvite();

  return (
    <InviteGate unlocked={unlocked}>
      <Wizard />
    </InviteGate>
  );
}

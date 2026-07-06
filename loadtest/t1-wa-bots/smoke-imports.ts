// Offline smoke: verifies the protobuf imports/encode/decode the bot relies on.
// Run: npx tsx smoke-imports.ts   (no network, no prod contact)
import {
    apiVersionHash,
    ClientToServerMessage,
    ServerToClientMessage,
    PositionMessage_Direction,
    AvailabilityStatus,
} from "@workadventure/messages";

const m = ClientToServerMessage.encode({
    message: {
        $case: "userMovesMessage",
        userMovesMessage: {
            position: { x: 1, y: 2, direction: PositionMessage_Direction.DOWN, moving: true },
            viewport: { left: 0, top: 0, right: 10, bottom: 10 },
        },
    },
}).finish();
const rt = ClientToServerMessage.decode(m);
if (rt.message?.$case !== "userMovesMessage") throw new Error("roundtrip failed");
void ServerToClientMessage; // decoder used by bot at runtime
console.log(`IMPORTS_OK apiVersionHash=${apiVersionHash} bytes=${m.length} status=${AvailabilityStatus.ONLINE}`);

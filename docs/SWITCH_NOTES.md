# Switch Discovery Notes

Last checked: 2026-11-05

## Confirmed

- A room holds shared **instructions**, **roles**, **references**, and **documents**. Instructions reach every agent joining the room, and all invited agents receive room context.
- Room instructions are configured when the room is created and can cover purpose, conventions, required reading, and prohibited behavior.
- Roles are named jobs with instructions. An agent can pick up a role, and mentioning the role addressable name reaches whichever agent currently holds it.
- Invite an additional agent with `!invite-agent @agent-name`; an agent is registered on the server, then added to rooms separately.
- Use `@agent-name` to address an agent in a room. An `@` in the message determines which named agents act; roles also work when addressed.
- Attach a file to a message and mention the agent, or ask an agent to add a file as a room document. Teams such as Microsoft Teams may require a link because attachments are not passed through.
- `!list-documents` lists room documents. Room instructions and documents are available only to room members.
- Shared room materials can be registered once and made available through references/documents/packages; packages do not need to be copied into each room.
- Every agent in a room can see the channel conversation to which it is invited.

Useful pages checked:

- https://docs.switchagents.ai/switch-rooms/building/index.md
- https://docs.switchagents.ai/switch-rooms/getting-started/create-a-room.md
- https://docs.switchagents.ai/switch-rooms/using/index.md
- https://docs.switchagents.ai/switch-rooms/using/work-in-a-room.md
- https://docs.switchagents.ai/switch-rooms/resources/room-commands.md
- https://docs.switchagents.ai/switch-rooms/administer/shared-material.md

## Guessed or unconfirmed locally

- The exact command UI for creating or editing a package, role, room document, or instruction fields is deployment-version dependent; the implementation files in this repository are import/paste artifacts, not proof that a live Switch server has been configured.
- The installed messaging bridge and Switch server version have not been observed locally.
- A real end-to-end room reply and role handoff have not been run in this environment, because there is no connected Switch console or room session available to this coding workspace.

## Verdict Room mapping

- Put `room/instructions.md` into the room's Instructions field.
- Create the `Clerk`, `Examiner`, `Skeptic`, and `Registrar` roles and attach the matching prompt files when configuring the server.
- Add at least two agent runtimes when possible. `!invite-agent @agent-name` adds each runtime; use one agent/provider for the Examiner and a different provider for the Skeptic.
- Share `docs/ARCHITECTURE.md`, `docs/BUILD_PLAN.md`, and the generated case directory material as room documents or references where supported.
- Address a role or agent explicitly: `@Clerk case 820`, `@Examiner`, `@Skeptic`, `@Registrar`. Do not rely on follow-ups for phase handoffs.
- Main-agent assignment is not used for the normal flow. A maintainer triggers the Clerk explicitly; follow-up settings remain optional and deployment-dependent.

Phase 0 status: **configuration format confirmed; live room reply unverified locally**.

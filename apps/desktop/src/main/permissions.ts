import type { Session } from "electron";

export function lockDownPermissions(session: Session): void {
  session.setPermissionCheckHandler(() => false);
  session.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  session.setDevicePermissionHandler(() => false);
}


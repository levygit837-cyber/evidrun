const path = require("node:path");

module.exports = {
  packagerConfig: {
    asar: true,
    appBundleId: "dev.evidrun.app",
    appCategoryType: "public.app-category.developer-tools",
    extraResource: [path.resolve(__dirname, "resources/backend")],
    osxSign: process.env.EVIDRUN_CODESIGN === "1" ? {} : undefined,
    osxNotarize: process.env.EVIDRUN_NOTARIZE === "1"
      ? { keychainProfile: process.env.EVIDRUN_NOTARY_PROFILE }
      : undefined,
  },
  makers: [
    { name: "@electron-forge/maker-zip", platforms: ["darwin"] },
    { name: "@electron-forge/maker-dmg", config: { format: "ULFO" } },
  ],
};


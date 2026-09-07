EnviroChem Studio v2.21 launcher hotfix
=======================================

This patch repairs the Windows folder-path and occupied-port startup errors.

Apply it to an existing v2.21 installation
------------------------------------------
1. Close the EnviroChem terminal with Ctrl+C.
2. Extract this ZIP directly into the existing
   EnviroChem_Studio_v2_21_EVIDENCE_HOME_SAFETY folder.
3. Allow Windows to replace START_ENVIROCHEM.bat and
   ENVIROCHEM_TOOLS.bat when prompted.
4. Confirm that app\launcher_support.py exists.
5. Double-click START_ENVIROCHEM.bat.

Your data folder and saved projects are not included in this patch and are not
removed or overwritten.

New behaviour
-------------
- Folder names containing spaces are supported.
- If the same EnviroChem build is already running, it is reopened.
- If another application owns the configured port, the next available local
  port is selected automatically.

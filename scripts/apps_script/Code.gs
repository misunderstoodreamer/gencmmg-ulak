/**
 * Genç MMG — request attachment uploader.
 *
 * Deploy from the Google account that should own the files (e.g. gencmmg@gmail.com):
 *   1. Run setup() once from the editor and copy UPLOAD_TOKEN from the execution log.
 *   2. Deploy > New deployment > Web app: Execute as "Me", Who has access "Anyone".
 *   3. Put the web app URL and the token into [drive] in secrets.toml.
 *
 * Every request must carry the token; without it the endpoint rejects all actions.
 */

const FOLDER_NAME = 'Genç MMG Talep Ekleri';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const token = PropertiesService.getScriptProperties().getProperty('UPLOAD_TOKEN');
    if (!token || body.token !== token) {
      return respond_({ ok: false, error: 'unauthorized' });
    }

    switch (body.action) {
      case 'ping':
        return respond_({ ok: true, account: Session.getEffectiveUser().getEmail(), folder: folder_().getUrl() });

      case 'upload': {
        const blob = Utilities.newBlob(
          Utilities.base64Decode(body.data),
          body.mimeType || 'application/octet-stream',
          body.name
        );
        const file = folder_().createFile(blob);
        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        return respond_({ ok: true, id: file.getId(), url: file.getUrl() });
      }

      case 'delete':
        DriveApp.getFileById(body.id).setTrashed(true);
        return respond_({ ok: true });

      default:
        return respond_({ ok: false, error: 'unknown action' });
    }
  } catch (err) {
    return respond_({ ok: false, error: String(err) });
  }
}

/** Run once from the editor: creates the token and the upload folder. */
function setup() {
  // Granular consent lets users approve only some scopes; re-prompt until all are granted.
  ScriptApp.requireAllScopes(ScriptApp.AuthMode.FULL);

  // Verify write access now rather than on the first real upload.
  folder_().createFile('izin-testi.txt', 'ok').setTrashed(true);

  const props = PropertiesService.getScriptProperties();
  let token = props.getProperty('UPLOAD_TOKEN');
  if (!token) {
    token = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('UPLOAD_TOKEN', token);
  }
  Logger.log('Klasör: ' + folder_().getUrl());
  Logger.log('UPLOAD_TOKEN: ' + token);
}

function folder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('FOLDER_ID');
  if (id) {
    try {
      return DriveApp.getFolderById(id);
    } catch (err) {
      // Folder was deleted; fall through and recreate it.
    }
  }
  const existing = DriveApp.getFoldersByName(FOLDER_NAME);
  const folder = existing.hasNext() ? existing.next() : DriveApp.createFolder(FOLDER_NAME);
  props.setProperty('FOLDER_ID', folder.getId());
  return folder;
}

function respond_(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(ContentService.MimeType.JSON);
}

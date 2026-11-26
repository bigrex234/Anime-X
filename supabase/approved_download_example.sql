-- Run manually only when you have verified distribution rights.
-- Keep is_active false until the URL and permission are confirmed.
insert into public.downloadable_assets
  (anime_id, title, description, source_url, file_name, mime_type, rights_note, is_active)
values
  (12345, 'Example rights-cleared bonus video',
   'Replace with a description of the authorised file.',
   'https://example.org/replace-with-authorized-file.mp4',
   'bonus-video.mp4', 'video/mp4',
   'Replace with a documented public-domain licence or written distribution permission.',
   false);

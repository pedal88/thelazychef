"""Resources Blueprint: the public 'Become a chef' articles and their admin editor."""
import uuid

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from slugify import slugify

from database.models import Resource, db
from routes._flat import FlatBlueprint
from routes._shared import get_storage
from utils.decorators import admin_required

resources_bp = FlatBlueprint("resources", __name__)


@resources_bp.route('/become-a-chef')
def resources_list():
    resources = db.session.execute(db.select(Resource).where(Resource.status == 'published').order_by(Resource.created_at.desc())).scalars().all()
    return render_template('resources.html', resources=resources)

@resources_bp.route('/become-a-chef/<slug>')
def resource_detail(slug):
    # Try fetching by slug first
    resource = db.session.execute(db.select(Resource).where(Resource.slug == slug)).scalar_one_or_none()
    
    # Fallback to ID if not found (for legacy support if needed, though slug is preferred)
    if not resource:
         try:
             r_id = int(slug)
             resource = db.session.get(Resource, r_id)
         except ValueError:
             pass

    if not resource:
        flash("Article not found", "error")
        return redirect(url_for('resources_list'))
    
    # Related resources are already available via relationship
    # But for template compatibility if it expects a list, resource.related_resources is a dynamic loader
    # so we need to iterate or convert to list. The template iterates.
    # We might need to pass related_resources explicitly if template expects it separate from resource object
    # The existing template uses `related_resources` variable passed to it.
    
    # Convert dynamic relationship query to list
    related = resource.related_resources.all()
        
    return render_template('resource_detail.html', resource=resource, related_resources=related)


@resources_bp.route('/admin/resources')
@login_required
@admin_required
def admin_resources_list():
    resources = db.session.execute(db.select(Resource).order_by(Resource.created_at.desc())).scalars().all()
    return render_template('admin/resources_list.html', resources=resources)

@resources_bp.route('/admin/resources/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_resource_new():
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        if not slug:
            slug = slugify(title)
            
        summary = request.form.get('summary')
        content_markdown = request.form.get('content_markdown')
        tags = request.form.get('tags')
        status = request.form.get('status', 'draft')
        
        # Image Upload
        image_filename = None
        file = request.files.get('cover_image')
        if file and file.filename != '':
            new_filename = f"resource_{uuid.uuid4().hex[:8]}_{file.filename}"
            # Save returns the public URL (path for local, http url for GCS)
            public_url = get_storage().save(file.read(), new_filename, "resources")
            image_filename = public_url
        
        resource = Resource(
            title=title,
            slug=slug,
            summary=summary,
            content_markdown=content_markdown,
            image_filename=image_filename,
            tags=tags,
            status=status
        )
        
        # Handle Relations
        related_ids = request.form.getlist('related_ids')
        for r_id in related_ids:
            related = db.session.get(Resource, int(r_id))
            if related:
                resource.related_resources.append(related)
                
        db.session.add(resource)
        try:
            db.session.commit()
            flash('Resource created successfully!', 'success')
            return redirect(url_for('admin_resources_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating resource: {str(e)}', 'error')
    
    all_resources = db.session.execute(db.select(Resource).order_by(Resource.title)).scalars().all()
    return render_template('admin/resource_editor.html', resource=None, all_resources=all_resources)

@resources_bp.route('/admin/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_resource_edit(resource_id):
    resource = db.session.get(Resource, resource_id)
    if not resource:
        flash('Resource not found', 'error')
        return redirect(url_for('admin_resources_list'))

    if request.method == 'POST':
        resource.title = request.form.get('title')
        
        slug = request.form.get('slug')
        if not slug:
            slug = slugify(resource.title)
        resource.slug = slug
        
        resource.summary = request.form.get('summary')
        resource.content_markdown = request.form.get('content_markdown')
        resource.tags = request.form.get('tags')
        resource.status = request.form.get('status', 'draft')
        
        # Image Upload
        file = request.files.get('cover_image')
        if file and file.filename != '':
            new_filename = f"resource_{uuid.uuid4().hex[:8]}_{file.filename}"
            public_url = get_storage().save(file.read(), new_filename, "resources")
            resource.image_filename = public_url
        
        # Handle Relations (Update: clear and re-add)
        resource.related_resources = [] # This empties the relationship
        related_ids = request.form.getlist('related_ids')
        for r_id in related_ids:
             related = db.session.get(Resource, int(r_id))
             if related:
                 resource.related_resources.append(related)
        
        try:
            db.session.commit()
            flash('Resource updated successfully!', 'success')
            return redirect(url_for('admin_resources_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating resource: {str(e)}', 'error')

    all_resources = db.session.execute(db.select(Resource).order_by(Resource.title)).scalars().all()
    return render_template('admin/resource_editor.html', resource=resource, all_resources=all_resources)


@resources_bp.route('/api/cms/upload-image', methods=['POST'])
@login_required
@admin_required
def cms_upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = f"cms_{uuid.uuid4().hex[:8]}_{file.filename}"
        public_url = get_storage().save(file.read(), filename, "cms-uploads")
        return jsonify({
            'data': {
                'filePath': public_url
            }
        })
    return jsonify({'error': 'Upload failed'}), 500

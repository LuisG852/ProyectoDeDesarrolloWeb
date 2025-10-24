from flask import Flask, render_template, request, jsonify, session, send_file, redirect
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
from datetime import datetime
import os

# Inicialización de Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '1234')

# Configuración de la base de datos
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Producción - Render proporciona DATABASE_URL automáticamente
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
    elif DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Desarrollo
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://supermarket_user:93gweNrUZKgLaQeVQiVh990Rz3pJeoZp@dpg-d3njp6buibrs738felb0-a.oregon-postgres.render.com:5432/supermarket_db_rqjm'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ========================================
# RUTAS PARA RENDERIZAR PÁGINAS HTML
# ========================================

@app.route('/')
def index():
    """Ruta principal - redirige al login"""
    return render_template('login.html')


@app.route('/login-page')
def login_page():
    """Renderiza la página de login"""
    return render_template('login.html')


@app.route('/registro-page')
def registro_page():
    """Renderiza la página de registro"""
    return render_template('registro.html')


@app.route('/checkout')
def checkout_page():
    """Renderiza la página de checkout"""
    if 'usuario' not in session:
        return render_template('login.html')
    return render_template('checkout.html')


@app.route('/tarjeta')
def tarjeta_page():
    """Renderiza la página de pago con tarjeta"""
    if 'usuario' not in session:
        return render_template('login.html')
    return render_template('tarjeta.html')


@app.route('/dashboard')
def dashboard():
    """Renderiza el dashboard - solo si hay sesión activa"""
    if 'usuario' not in session:
        return render_template('login.html')

    # Verificar que NO sea admin
    if session.get('rol') == 'admin':
        return redirect('/dashboard-admin')

    return render_template('dashboard.html')


@app.route('/dashboard-admin')
def dashboard_admin():
    """Renderiza el dashboard admin - solo para admin"""
    if 'usuario' not in session:
        return render_template('login.html')

    # Verificar que SEA admin
    if session.get('rol') != 'admin':
        return redirect('/dashboard')

    return render_template('dashboard_admin.html')


# ========================================
# ENDPOINTS DE AUTENTICACIÓN
# ========================================

from flask import request, jsonify, session

# ========================================
# LOGIN
# ========================================
@app.route('/login', methods=['POST'])
def login():
    """Endpoint para iniciar sesión con redirección según rol"""
    try:
        data = request.get_json()
        usuario = data.get('usuario')
        contrasena = data.get('contrasena')

        if not usuario or not contrasena:
            return jsonify({'success': False, 'message': 'Usuario y contraseña son requeridos'}), 400

        cursor = db.session.connection().connection.cursor()
        cursor.execute("""
            SELECT id_usuario, usuario, contrasena, rol, nombre, email, telefono
            FROM usuario 
            WHERE usuario = %s
        """, (usuario,))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        columns = ['id_usuario', 'usuario', 'contrasena', 'rol', 'nombre', 'email', 'telefono']
        user_data = dict(zip(columns, result))
        
        if user_data['contrasena'] == contrasena:
            session['usuario_id'] = user_data['id_usuario']
            session['usuario'] = user_data['usuario']
            session['rol'] = user_data['rol']

            redirect_url = '/dashboard-admin' if user_data['rol'] == 'admin' else '/dashboard'

            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'usuario': user_data['usuario'],
                'rol': user_data['rol'],
                'redirect': redirect_url
            })
        else:
            return jsonify({'success': False, 'message': 'Contraseña incorrecta'}), 401

    except Exception as e:
        db.session.rollback()
        print(f"Error en login: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# REGISTRO
# ========================================
@app.route('/registro', methods=['POST'])
def registro():
    """Endpoint para registrar nuevo usuario"""
    try:
        data = request.get_json()
        usuario = data.get('usuario')
        contrasena = data.get('contrasena')
        rol = data.get('rol', 'cliente')  # Por defecto cliente
        nombre = data.get('nombre')
        email = data.get('email')
        telefono = data.get('telefono')
        nit = data.get('nit')
        direccion = data.get('direccion')

        if not usuario or not contrasena or not nombre:
            return jsonify({'success': False, 'message': 'Usuario, contraseña y nombre son requeridos'}), 400

        cursor = db.session.connection().connection.cursor()
        cursor.execute("SELECT id_usuario FROM usuario WHERE usuario = %s", (usuario,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'El usuario ya existe'}), 409

        cursor.execute("""
            INSERT INTO usuario (usuario, contrasena, rol, nombre, email, telefono, nit, direccion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario, contrasena, rol, nombre, email, telefono, nit, direccion))
        
        db.session.commit()

        return jsonify({'success': True, 'message': 'Usuario registrado exitosamente'})

    except Exception as e:
        db.session.rollback()
        print(f"Error en registro: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    """Endpoint para cerrar sesión"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        })
    except Exception as e:
        print(f"Error en logout: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS DE DATOS
# ========================================

@app.route('/obtener-usuario')
def obtener_usuario():
    """Obtiene el usuario de la sesión actual"""
    try:
        if 'usuario' in session:
            return jsonify({
                'success': True,
                'usuario': session['usuario'],
                'usuario_id': session['usuario_id']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
    except Exception as e:
        print(f"Error en obtener_usuario: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS PARA CONSULTAS DE DATOS
# ========================================

@app.route('/productos')
def listar_productos():
    """Lista todos los productos"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT 
                p.id_producto, 
                p.nombre, 
                p.precio, 
                p.marca,
                p.id_subcategoria,
                p.id_proveedor,
                s.nombre as subcategoria,
                s.id_categoria,
                pr.nombre as proveedor,
                c.nombre as categoria
            FROM producto p
            LEFT JOIN subcategoria s ON p.id_subcategoria = s.id_subcategoria
            LEFT JOIN proveedor pr ON p.id_proveedor = pr.id_proveedor
            LEFT JOIN categoria c ON s.id_categoria = c.id_categoria
            ORDER BY p.id_producto
        """)
        
        results = cursor.fetchall()
        
        columns = [
            'id_producto', 'nombre', 'precio', 'marca', 
            'id_subcategoria', 'id_proveedor', 'subcategoria',
            'id_categoria', 'proveedor', 'categoria'
        ]
        productos = [dict(zip(columns, row)) for row in results]

        return jsonify({
            'success': True,
            'productos': productos
        })

    except Exception as e:
        print(f"Error en listar_productos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/categorias')
def listar_categorias():
    """Lista todas las categorías"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT id_categoria, nombre, descripcion
            FROM categoria 
            ORDER BY id_categoria
        """)
        
        results = cursor.fetchall()
        
        columns = ['id_categoria', 'nombre', 'descripcion']
        categorias = [dict(zip(columns, row)) for row in results]

        return jsonify({
            'success': True,
            'categorias': categorias
        })

    except Exception as e:
        print(f"Error en listar_categorias: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/subcategorias')
def listar_subcategorias():
    """Lista todas las subcategorías"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT 
                s.id_subcategoria,
                s.nombre,
                s.descripcion,
                s.id_categoria,
                c.nombre as categoria_nombre
            FROM subcategoria s
            LEFT JOIN categoria c ON s.id_categoria = c.id_categoria
            ORDER BY s.id_subcategoria
        """)
        
        results = cursor.fetchall()
        
        columns = ['id_subcategoria', 'nombre', 'descripcion', 'id_categoria', 'categoria_nombre']
        subcategorias = [dict(zip(columns, row)) for row in results]
        
        return jsonify({
            'success': True,
            'subcategorias': subcategorias
        })
        
    except Exception as e:
        print(f"Error en listar_subcategorias: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/proveedores')
def listar_proveedores():
    """Lista todos los proveedores"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT id_proveedor, nombre, direccion, telefono
            FROM proveedor 
            ORDER BY id_proveedor
        """)
        
        results = cursor.fetchall()
        
        columns = ['id_proveedor', 'nombre', 'direccion', 'telefono']
        proveedores = [dict(zip(columns, row)) for row in results]

        return jsonify({
            'success': True,
            'proveedores': proveedores
        })

    except Exception as e:
        print(f"Error en listar_proveedores: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/crear-venta', methods=['POST'])
def crear_venta():
    """Crear una nueva venta desde el carrito"""
    try:
        data = request.get_json()
        items = data.get('items')
        metodo_pago = data.get('metodo_pago', 'Efectivo')
        
        # Obtener id_usuario desde sesión
        id_usuario = session.get('usuario_id')
        if not id_usuario:
            return jsonify({'success': False, 'message': 'Usuario no autenticado'}), 401

        if not items or len(items) == 0:
            return jsonify({'success': False, 'message': 'El carrito está vacío'}), 400
        
        # Validar cada item
        for item in items:
            if 'id_producto' not in item:
                return jsonify({'success': False, 'message': f"Falta id_producto en uno de los productos"}), 400
            if 'cantidad' not in item or 'precio_unitario' not in item:
                return jsonify({'success': False, 'message': f"Falta cantidad o precio en el producto {item.get('id_producto')}"}), 400

            # Convertir a tipos correctos
            try:
                item['cantidad'] = int(item['cantidad'])
                item['precio_unitario'] = float(item['precio_unitario'])
            except ValueError:
                return jsonify({'success': False, 'message': f"Cantidad o precio inválido en el producto {item.get('id_producto')}"}), 400
        
        cursor = db.session.connection().connection.cursor()
        
        # Calcular totales
        subtotal = sum(item['precio_unitario'] * item['cantidad'] for item in items)
        iva = subtotal * 0.12
        total = subtotal + iva
        
        # Generar número de factura
        cursor.execute("SELECT MAX(id_venta) FROM venta")
        result = cursor.fetchone()
        max_id = result[0] if result[0] is not None else 0
        factura = f"F{str(max_id + 1).zfill(6)}"
        
        # Insertar venta
        cursor.execute("""
            INSERT INTO venta (factura, usuario_id, subtotal, iva, total, metodo_pago)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_venta
        """, (factura, id_usuario, subtotal, iva, total, metodo_pago))
        
        id_venta = cursor.fetchone()[0]
        
        # Insertar detalles de venta
        for item in items:
            subtotal_item = item['precio_unitario'] * item['cantidad']
            cursor.execute("""
                INSERT INTO detalle_venta (id_venta, id_producto, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_venta, item['id_producto'], item['cantidad'], item['precio_unitario'], subtotal_item))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Venta creada exitosamente',
            'id_venta': id_venta,
            'factura': factura,
            'total': float(total)
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en crear_venta: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

from flask import Flask, jsonify, send_file
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

@app.route('/generar-factura/<int:id_venta>')
def generar_factura(id_venta):
    """Genera y descarga la factura en PDF"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        # Obtener datos de la venta y del usuario (cliente)
        cursor.execute("""
            SELECT 
                v.id_venta,
                v.factura,
                v.fecha,
                v.subtotal,
                v.iva,
                v.total,
                v.metodo_pago,
                u.nombre as cliente_nombre
            FROM venta v
            LEFT JOIN usuario u ON v.usuario_id = u.id_usuario
            WHERE v.id_venta = %s
        """, (id_venta,))
        
        venta_data = cursor.fetchone()
        
        if not venta_data:
            return jsonify({
                'success': False,
                'message': 'Venta no encontrada'
            }), 404
        
        # Obtener detalles de la venta
        cursor.execute("""
            SELECT 
                p.nombre,
                p.marca,
                dv.cantidad,
                dv.precio_unitario,
                dv.subtotal
            FROM detalle_venta dv
            LEFT JOIN producto p ON dv.id_producto = p.id_producto
            WHERE dv.id_venta = %s
        """, (id_venta,))
        
        detalles = cursor.fetchall()
        
        # Crear PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        elements.append(Paragraph("FACTURA DE VENTA", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        info_data = [
            ['Factura:', venta_data[1]],
            ['Fecha:', venta_data[2].strftime('%d/%m/%Y %H:%M')],
            ['Método de Pago:', venta_data[6]],
            ['Cliente:', venta_data[7] or 'Cliente General']
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*inch))
        
        productos_data = [['Producto', 'Marca', 'Cant.', 'Precio Unit.', 'Total']]
        for detalle in detalles:
            productos_data.append([
                detalle[0],
                detalle[1] or 'N/A',
                str(detalle[2]),
                f'Q{float(detalle[3]):.2f}',
                f'Q{float(detalle[4]):.2f}'
            ])
        
        productos_table = Table(productos_data, colWidths=[2.5*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch])
        productos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(productos_table)
        elements.append(Spacer(1, 0.5*inch))
        
        totales_data = [
            ['', '', '', 'Subtotal:', f'Q{float(venta_data[3]):.2f}'],
            ['', '', '', 'IVA (12%):', f'Q{float(venta_data[4]):.2f}'],
            ['', '', '', 'TOTAL:', f'Q{float(venta_data[5]):.2f}']
        ]
        
        totales_table = Table(totales_data, colWidths=[2.5*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch])
        totales_table.setStyle(TableStyle([
            ('FONTNAME', (3, 0), (3, 1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 2), (3, 2), 'Helvetica-Bold'),
            ('FONTNAME', (4, 2), (4, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (3, 2), (4, 2), 12),
            ('TEXTCOLOR', (3, 2), (4, 2), colors.HexColor('#667eea')),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('LINEABOVE', (3, 2), (4, 2), 2, colors.HexColor('#667eea')),
        ]))
        elements.append(totales_table)
        
        elements.append(Spacer(1, 1*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph("Gracias por su compra", footer_style))
        elements.append(Paragraph("Sistema de Ventas", footer_style))
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Factura_{venta_data[1]}.pdf'
        )
    
    except Exception as e:
        print(f"Error en generar_factura: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS ADMIN - ESTADÍSTICAS
# ========================================

@app.route('/admin/estadisticas', methods=['GET'])
def admin_estadisticas():
    """Obtiene estadísticas generales del sistema"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        # Total de productos
        cursor.execute("SELECT COUNT(*) FROM producto")
        total_productos = cursor.fetchone()[0]
        
        # Total en ventas
        cursor.execute("SELECT COALESCE(SUM(total), 0) FROM venta")
        total_ventas = float(cursor.fetchone()[0])
        
        # Total de facturas
        cursor.execute("SELECT COUNT(*) FROM venta")
        total_facturas = cursor.fetchone()[0]
        
        # Total de clientes
        cursor.execute("SELECT COUNT(*) FROM usuario WHERE rol = 'cliente'")
        total_clientes = cursor.fetchone()[0]
        
        return jsonify({
            'success': True,
            'total_productos': total_productos,
            'total_ventas': total_ventas,
            'total_facturas': total_facturas,
            'total_clientes': total_clientes
        })
        
    except Exception as e:
        print(f"Error en admin_estadisticas: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS ADMIN - PRODUCTOS
# ========================================

@app.route('/admin/productos', methods=['GET'])
def admin_get_productos():
    """Lista todos los productos para admin"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT 
                p.id_producto,
                p.nombre,
                p.precio,
                p.marca,
                c.nombre as categoria,
                s.nombre as subcategoria,
                pr.nombre as proveedor,
                p.id_subcategoria,
                p.id_proveedor,
                s.id_categoria
            FROM producto p
            LEFT JOIN subcategoria s ON p.id_subcategoria = s.id_subcategoria
            LEFT JOIN categoria c ON s.id_categoria = c.id_categoria
            LEFT JOIN proveedor pr ON p.id_proveedor = pr.id_proveedor
            ORDER BY p.id_producto
        """)
        
        results = cursor.fetchall()
        
        columns = [
            'id_producto', 'nombre', 'precio', 'marca',
            'categoria', 'subcategoria', 'proveedor',
            'id_subcategoria', 'id_proveedor', 'id_categoria'
        ]
        productos = [dict(zip(columns, row)) for row in results]
        
        return jsonify({
            'success': True,
            'productos': productos
        })
        
    except Exception as e:
        print(f"Error en admin_get_productos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/producto/<int:id>', methods=['GET'])
def admin_get_producto(id):
    """Obtiene un producto específico"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT 
                p.id_producto,
                p.nombre,
                p.precio,
                p.marca,
                p.id_subcategoria,
                p.id_proveedor,
                s.id_categoria
            FROM producto p
            LEFT JOIN subcategoria s ON p.id_subcategoria = s.id_subcategoria
            WHERE p.id_producto = %s
        """, (id,))
        
        result = cursor.fetchone()
        
        if not result:
            return jsonify({
                'success': False,
                'message': 'Producto no encontrado'
            }), 404
        
        columns = [
            'id_producto', 'nombre', 'precio', 'marca',
            'id_subcategoria', 'id_proveedor', 'id_categoria'
        ]
        producto = dict(zip(columns, result))
        
        return jsonify({
            'success': True,
            'producto': producto
        })
        
    except Exception as e:
        print(f"Error en admin_get_producto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/producto', methods=['POST'])
def admin_create_producto():
    """Crea un nuevo producto"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        precio = data.get('precio')
        marca = data.get('marca')
        id_subcategoria = data.get('id_subcategoria')
        id_proveedor = data.get('id_proveedor')
        
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            INSERT INTO producto (nombre, precio, marca, id_subcategoria, id_proveedor)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_producto
        """, (nombre, precio, marca, id_subcategoria, id_proveedor))
        
        id_producto = cursor.fetchone()[0]
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto creado exitosamente',
            'id_producto': id_producto
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en admin_create_producto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/producto/<int:id>', methods=['PUT'])
def admin_update_producto(id):
    """Actualiza un producto existente"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        precio = data.get('precio')
        marca = data.get('marca')
        id_subcategoria = data.get('id_subcategoria')
        id_proveedor = data.get('id_proveedor')
        
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            UPDATE producto
            SET nombre = %s,
                precio = %s,
                marca = %s,
                id_subcategoria = %s,
                id_proveedor = %s
            WHERE id_producto = %s
        """, (nombre, precio, marca, id_subcategoria, id_proveedor, id))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto actualizado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en admin_update_producto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/producto/<int:id>', methods=['DELETE'])
def admin_delete_producto(id):
    """Elimina un producto"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("DELETE FROM producto WHERE id_producto = %s", (id,))
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en admin_delete_producto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS ADMIN - CATEGORÍAS Y SUBCATEGORÍAS
# ========================================

@app.route('/admin/categorias', methods=['GET'])
def admin_get_categorias():
    """Lista todas las categorías"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("SELECT id_categoria, nombre FROM categoria ORDER BY nombre")
        
        results = cursor.fetchall()
        
        columns = ['id_categoria', 'nombre']
        categorias = [dict(zip(columns, row)) for row in results]
        
        return jsonify({
            'success': True,
            'categorias': categorias
        })
        
    except Exception as e:
        print(f"Error en admin_get_categorias: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/subcategorias/<int:id_categoria>', methods=['GET'])
def admin_get_subcategorias(id_categoria):
    """Obtiene subcategorías de una categoría específica"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT id_subcategoria, nombre 
            FROM subcategoria 
            WHERE id_categoria = %s
            ORDER BY nombre
        """, (id_categoria,))
        
        results = cursor.fetchall()
        
        columns = ['id_subcategoria', 'nombre']
        subcategorias = [dict(zip(columns, row)) for row in results]
        
        return jsonify({
            'success': True,
            'subcategorias': subcategorias
        })
        
    except Exception as e:
        print(f"Error en admin_get_subcategorias: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS ADMIN - PROVEEDORES
# ========================================

@app.route('/admin/proveedores', methods=['GET'])
def admin_get_proveedores():
    """Lista todos los proveedores"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("SELECT id_proveedor, nombre FROM proveedor ORDER BY nombre")
        
        results = cursor.fetchall()
        
        columns = ['id_proveedor', 'nombre']
        proveedores = [dict(zip(columns, row)) for row in results]
        
        return jsonify({
            'success': True,
            'proveedores': proveedores
        })
        
    except Exception as e:
        print(f"Error en admin_get_proveedores: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS ADMIN - FACTURAS
# ========================================

@app.route('/admin/facturas', methods=['GET'])
def admin_get_facturas():
    """Lista todas las facturas con sus productos"""
    try:
        cursor = db.session.connection().connection.cursor()
        
        # Obtener todas las ventas
        cursor.execute("""
            SELECT 
                v.id_venta,
                v.factura,
                v.fecha,
                v.total,
                v.metodo_pago,
                u.nombre as cliente
            FROM venta v
            LEFT JOIN usuario u ON v.usuario_id = u.id_usuario
            ORDER BY v.fecha DESC
        """)
        
        ventas = cursor.fetchall()
        
        facturas = []
        for venta in ventas:
            # Obtener productos de cada venta
            cursor.execute("""
                SELECT 
                    p.nombre,
                    dv.cantidad,
                    dv.precio_unitario,
                    dv.subtotal
                FROM detalle_venta dv
                INNER JOIN producto p ON dv.id_producto = p.id_producto
                WHERE dv.id_venta = %s
            """, (venta[0],))
            
            productos = cursor.fetchall()
            
            facturas.append({
                'id_venta': venta[0],
                'factura': venta[1],
                'fecha': venta[2].isoformat(),
                'total': float(venta[3]),
                'metodo_pago': venta[4],
                'cliente': venta[5],
                'productos': [
                    {
                        'nombre': prod[0],
                        'cantidad': prod[1],
                        'precio_unitario': float(prod[2]),
                        'subtotal': float(prod[3])
                    }
                    for prod in productos
                ]
            })
        
        return jsonify({
            'success': True,
            'facturas': facturas
        })
        
    except Exception as e:
        print(f"Error en admin_get_facturas: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ENDPOINTS DE CONTACTO
# ========================================

@app.route('/contacto', methods=['POST'])
def enviar_contacto():
    """Endpoint para enviar formulario de contacto"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        email = data.get('email')
        telefono = data.get('telefono', '')
        mensaje = data.get('mensaje')
        
        if not nombre or not email or not mensaje:
            return jsonify({
                'success': False,
                'message': 'Nombre, email y mensaje son requeridos'
            }), 400
        
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            INSERT INTO contacto (nombre, email, telefono, mensaje)
            VALUES (%s, %s, %s, %s)
            RETURNING id_contacto
        """, (nombre, email, telefono, mensaje))
        
        id_contacto = cursor.fetchone()[0]
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '¡Mensaje enviado exitosamente! Te contactaremos pronto.',
            'id_contacto': id_contacto
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en enviar_contacto: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/contactos', methods=['GET'])
def admin_get_contactos():
    """Lista todos los mensajes de contacto (solo admin)"""
    try:
        if 'usuario' not in session or session.get('rol') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso no autorizado'
            }), 403
        
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            SELECT 
                id_contacto,
                nombre,
                email,
                telefono,
                mensaje,
                fecha,
                estado
            FROM contacto
            ORDER BY fecha DESC
        """)
        
        results = cursor.fetchall()
        
        columns = ['id_contacto', 'nombre', 'email', 'telefono', 'mensaje', 'fecha', 'estado']
        contactos = []
        
        for row in results:
            contacto = dict(zip(columns, row))
            if contacto['fecha']:
                contacto['fecha'] = contacto['fecha'].isoformat()
            contactos.append(contacto)
        
        return jsonify({
            'success': True,
            'contactos': contactos
        })
        
    except Exception as e:
        print(f"Error en admin_get_contactos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/contacto/<int:id>/estado', methods=['PUT'])
def admin_update_contacto_estado(id):
    """Actualiza el estado de un mensaje de contacto"""
    try:
        if 'usuario' not in session or session.get('rol') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso no autorizado'
            }), 403
        
        data = request.get_json()
        estado = data.get('estado')
        
        if estado not in ['pendiente', 'leido', 'resuelto']:
            return jsonify({
                'success': False,
                'message': 'Estado inválido'
            }), 400
        
        cursor = db.session.connection().connection.cursor()
        
        cursor.execute("""
            UPDATE contacto
            SET estado = %s
            WHERE id_contacto = %s
        """, (estado, id))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estado actualizado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error en admin_update_contacto_estado: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# INICIO DE LA APLICACIÓN
# ========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print("Iniciando aplicación Flask...")
    print(f"Servidor corriendo en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from usuarios.decorators import rol_requerido

from .models import Producto, Categoria


@login_required
def pantalla_cobro(request):
     """
     Pantalla de cobro (POS). En este Sprint 1 es solo la cáscara protegida
     por login: el flujo real de "escanear código → vuela al carrito",
     el vuelto rápido con billetes y el cierre de caja son de sprints
     siguientes.
     """
     return render(request, "ventas/pantalla_cobro.html")


# ========== LISTA DE PRODUCTOS ==========
@rol_requerido("Administrador")
def lista_productos(request):
     busqueda = request.GET.get('buscar', '')
     if busqueda:
         productos = Producto.objects.filter(
             Q(nombre__icontains=busqueda) |
             Q(descripcion__icontains=busqueda) |
             Q(categoria__nombre__icontains=busqueda)
         )
     else:
         productos = Producto.objects.all()

     productos = productos.order_by('nombre')

     return render(request, 'ventas/lista_productos.html', {
         'productos': productos,
         'busqueda': busqueda
     })


# ========== AGREGAR PRODUCTO (con opción de categoría nueva) ==========
@rol_requerido("Administrador")
def agregar_producto(request):
     if request.method == 'POST':
         nombre = request.POST.get('nombre', '').strip()
         descripcion = request.POST.get('descripcion', '').strip()
         precio = request.POST.get('precio', '').strip()
         stock = request.POST.get('stock', '').strip()
         categoria_id = request.POST.get('categoria', '').strip()
         nueva_categoria = request.POST.get('nueva_categoria', '').strip()

         errores = []

         if not nombre:
             errores.append('El nombre es obligatorio.')
         if not precio:
             errores.append('El precio es obligatorio.')
         if not stock:
             errores.append('El stock es obligatorio.')
         if not categoria_id and not nueva_categoria:
             errores.append('Debe seleccionar una categoría o crear una nueva.')

         if errores:
             categorias = Categoria.objects.all().order_by('nombre')
             return render(request, 'ventas/agregar_producto.html', {
                 'categorias': categorias,
                 'errores': errores,
                 'nombre': nombre,
                 'descripcion': descripcion,
                 'precio': precio,
                 'stock': stock,
                 'categoria_id': categoria_id,
                 'nueva_categoria': nueva_categoria
             })

         try:
             precio_val = float(precio)
         except (ValueError, TypeError):
             errores.append('El precio debe ser un número válido.')
         try:
             stock_val = int(stock)
         except (ValueError, TypeError):
             errores.append('El stock debe ser un número entero válido.')

         if errores:
             categorias = Categoria.objects.all().order_by('nombre')
             return render(request, 'ventas/agregar_producto.html', {
                 'categorias': categorias,
                 'errores': errores,
                 'nombre': nombre,
                 'descripcion': descripcion,
                 'precio': precio,
                 'stock': stock,
                 'categoria_id': categoria_id,
                 'nueva_categoria': nueva_categoria
             })

         # Si escribieron categoría nueva, la creamos
         if nueva_categoria:
             categoria, _ = Categoria.objects.get_or_create(nombre=nueva_categoria)
         else:
             categoria = get_object_or_404(Categoria, id=categoria_id)

         Producto.objects.create(
             nombre=nombre,
             descripcion=descripcion,
             precio=precio_val,
             stock=stock_val,
             categoria=categoria
         )
         messages.success(request, f'Producto "{nombre}" creado exitosamente.')
         return redirect('ventas:lista_productos')

     categorias = Categoria.objects.all().order_by('nombre')
     return render(request, 'ventas/agregar_producto.html', {
         'categorias': categorias
     })


@rol_requerido("Administrador")
def editar_producto(request, producto_id):
     producto = get_object_or_404(Producto, id=producto_id)

     if request.method == 'POST':
         nombre = request.POST.get('nombre', '').strip()
         descripcion = request.POST.get('descripcion', '').strip()
         precio = request.POST.get('precio', '').strip()
         stock = request.POST.get('stock', '').strip()
         categoria_id = request.POST.get('categoria', '').strip()
         nueva_categoria = request.POST.get('nueva_categoria', '').strip()
         activo = request.POST.get('activo') == 'on'

         errores = []

         if not nombre:
             errores.append('El nombre es obligatorio.')
         if not precio:
             errores.append('El precio es obligatorio.')
         if not stock:
             errores.append('El stock es obligatorio.')
         if not categoria_id and not nueva_categoria:
             errores.append('Debe seleccionar una categoría o crear una nueva.')

         if errores:
             categorias = Categoria.objects.all().order_by('nombre')
             return render(request, 'ventas/editar_producto.html', {
                 'categorias': categorias,
                 'producto': producto,
                 'errores': errores,
                 'nombre': nombre,
                 'descripcion': descripcion,
                 'precio': precio,
                 'stock': stock,
                 'categoria_id': categoria_id,
                 'nueva_categoria': nueva_categoria,
                 'activo': activo
             })

         try:
             precio_val = float(precio)
         except (ValueError, TypeError):
             errores.append('El precio debe ser un número válido.')
         try:
             stock_val = int(stock)
         except (ValueError, TypeError):
             errores.append('El stock debe ser un número entero válido.')

         if errores:
             categorias = Categoria.objects.all().order_by('nombre')
             return render(request, 'ventas/editar_producto.html', {
                 'categorias': categorias,
                 'producto': producto,
                 'errores': errores,
                 'nombre': nombre,
                 'descripcion': descripcion,
                 'precio': precio,
                 'stock': stock,
                 'categoria_id': categoria_id,
                 'nueva_categoria': nueva_categoria,
                 'activo': activo
             })

         if nueva_categoria:
             categoria, _ = Categoria.objects.get_or_create(nombre=nueva_categoria)
         else:
             categoria = get_object_or_404(Categoria, id=categoria_id)

         producto.nombre = nombre
         producto.descripcion = descripcion
         producto.precio = precio_val
         producto.stock = stock_val
         producto.categoria = categoria
         producto.activo = activo
         producto.save()
         messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
         return redirect('ventas:lista_productos')

     categorias = Categoria.objects.all().order_by('nombre')
     return render(request, 'ventas/editar_producto.html', {
         'categorias': categorias,
         'producto': producto
     })


@rol_requerido("Administrador")
def eliminar_producto(request, producto_id):
     producto = get_object_or_404(Producto, id=producto_id)

     if request.method == 'POST':
         nombre = producto.nombre
         producto.delete()
         messages.success(request, f'Producto "{nombre}" eliminado exitosamente.')
         return redirect('ventas:lista_productos')

     return render(request, 'ventas/eliminar_producto.html', {'producto': producto})


@rol_requerido("Administrador")
def toggle_producto(request, producto_id):
     producto = get_object_or_404(Producto, id=producto_id)
     producto.activo = not producto.activo
     producto.save()
     estado = 'activado' if producto.activo else 'desactivado'
     messages.success(request, f'Producto "{producto.nombre}" {estado} exitosamente.')
     return redirect('ventas:lista_productos')








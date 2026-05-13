function valor = f_obtener_coordenadas(Matriz, unit)
    % Asegura que la figura y la imagen ya existen antes de agregar elementos
    hold on;
    
    % Inicializa variables para el texto y el círculo
    hText = [];
    hCircle = [];
    
    while true
        [x, y, boton] = ginput(1); % Captura un solo clic
        
        if isempty(x) % Si se presiona Enter, termina
            break;
        end
        
        if boton == 1 % Solo guarda clics con el botón izquierdo
            coords = [round(x), round(y)]; % Guarda coordenadas enteras
            
            % Verifica que las coordenadas estén dentro de los límites de la matriz
            if coords(2) > 0 && coords(2) <= size(Matriz, 1) && coords(1) > 0 && coords(1) <= size(Matriz, 2)
                valor = Matriz(coords(2), coords(1)); % Accede al valor de la matriz (índice fila-columna)
                
                % Elimina el círculo anterior si existe
                if ishandle(hCircle)
                    delete(hCircle);
                end
                
                % Dibuja el nuevo punto
                hCircle = plot(x, y, 'ro', 'MarkerSize', 8, 'LineWidth', 2);
                
                % Elimina el texto anterior si existe
                if ishandle(hText)
                    delete(hText);
                end
                
                % Crea un nuevo texto con el valor seleccionado y la unidad
                hText = text(x + 10, y, sprintf('%.3f %s', valor, unit), ...
                    'Color', 'w', 'FontSize', 12, 'FontWeight', 'bold', ...
                    'BackgroundColor', 'k', 'EdgeColor', 'w');
            end
        end
    end
    hold off;
end

import { Injectable } from '@angular/core';
import { DiagramService } from './diagram.service';

@Injectable({ providedIn: 'root' })
export class RelationshipService {
	private sourceElement: any = null;
	private paper: any = null;
	private clickHandler: any = null;
	private currentType: string = 'association'; // por defecto

	constructor(private diagramService: DiagramService) {}

	/**
	 * Inicia el modo de creación de relación con un tipo específico
	 */
	startLinkCreation(
		paper: any,
		containerElement: HTMLElement,
		type: string = 'association'
	): void {
		this.paper = paper;
		this.sourceElement = null;
		this.currentType = type;
		// Cambiamos el cursor para indicar el modo de creación
		containerElement.style.cursor = 'crosshair';
		// Activamos el listener para la selección de elementos
		this.clickHandler = (cellView: any) => {
			const model = cellView.model;
			const isLink = !!model?.isLink?.();

			// Clase asociativa (notación UML): se elige una clase y la asociación de la que cuelga, en cualquier
			// orden, y se une la clase con el MEDIO de esa línea con un conector punteado sin multiplicidad.
			if (this.currentType === 'association-class') {
				if (!this.sourceElement) {
					this.sourceElement = model;
					return;
				}
				const first = this.sourceElement;
				const classCell = !first.isLink?.() ? first : (!isLink ? model : null);
				const association = first.isLink?.() ? first : (isLink ? model : null);
				const isAssociation = !!association && (association.get('relationType') || 'association') === 'association';
				if (classCell && isAssociation) {
					this.createTypedRelationship(classCell.id, association.id, this.currentType);
				}
				this.finishLinkCreation(containerElement);
				return;
			}

			// El resto de relaciones unen dos clases: una línea no puede ser uno de sus extremos.
			if (isLink) return;

			if (!this.sourceElement) {
				// Primera selección
				this.sourceElement = model;
			} else {
				// Segunda selección, creamos la relación
				this.createTypedRelationship(
					this.sourceElement.id,
					model.id,
					this.currentType
				);
				this.finishLinkCreation(containerElement);
			}
		};
		this.paper.on('cell:pointerclick', this.clickHandler);
	}

	/** Limpia el estado y desactiva el modo de creación de relación. */
	private finishLinkCreation(containerElement: HTMLElement): void {
		this.paper.off('cell:pointerclick', this.clickHandler);
		containerElement.style.cursor = 'default';
		this.sourceElement = null;
		this.clickHandler = null;
	}

	/**
	 * Crea una relación del tipo solicitado entre dos elementos (o, para la clase asociativa, entre una clase y una asociación)
	 */
  private createTypedRelationship(sourceId: string, targetId: string, type: string) {
    this.diagramService.createTypedRelationship(sourceId, targetId, type);
  }


	/**
	 * Cancela el modo de creación de relación
	 */
	cancelLinkCreation(containerElement: HTMLElement): void {
		if (this.paper && this.clickHandler) {
			this.paper.off('cell:pointerclick', this.clickHandler);
			containerElement.style.cursor = 'default';
			this.sourceElement = null;
			this.clickHandler = null;
			this.currentType = 'association';
		}
	}
}